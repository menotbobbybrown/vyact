const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../main.js'), 'utf8');

function fixture({allowed = true, reasons = ['restore'], unavailable = false, setup = false, holdBackend = false} = {}) {
    const order = [];
    let beforeQuit, finishBackend;
    const context = vm.createContext({
        isQuitting: false, shutdownComplete: false, shutdownNotice: null,
        serverSetupInProgress: setup, serverProc: {pid: 123, exitCode: null, signalCode: null},
        SHUTDOWN_TOKEN: 'secret', SHUTDOWN_CHECK_TIMEOUT_MS: 5000,
        crypto: {randomUUID: () => 'attempt'}, AbortSignal,
        fetch: async (_url, options) => {
            order.push(options.method);
            if (unavailable && options.method === 'POST') throw new Error('offline');
            return {ok: true, json: async () => ({pid: 123, allowed, reasons})};
        },
        restoreAndFocusMainWindow: () => order.push('focus'),
        mainWindow: {webContents: {isDestroyed: () => false, getURL: () => 'http://localhost:8000', send: (_, reasons) => order.push(reasons.join(','))}},
        initialSetupView: null,
        elasticsearchStartPromise: Promise.resolve(),
        runElasticsearchLifecycle: async action => order.push(action),
        log: () => {}, ipcMain: {handle() {}},
        app: {on: (_, callback) => {beforeQuit = callback;}, quit: () => order.push('quit')},
        autoUpdater: {quitAndInstall: () => order.push('install')},
        updateAppUpdateState: state => order.push(state.status),
    });
    vm.runInContext(source.slice(source.indexOf('function backendIsRunning()'), source.indexOf('ipcMain.handle("get-log-path"')), context);
    context.stopLocalRuntimes = async () => {
        order.push('backend');
        if (holdBackend) await new Promise(resolve => {finishBackend = resolve;});
    };
    return {context, order, quit: () => beforeQuit({preventDefault: () => order.push('prevent')}), finish: () => finishBackend()};
}

test('repeated quit cannot bypass cleanup and keeps the window visible', async () => {
    const f = fixture({holdBackend: true});
    const first = f.quit();
    await new Promise(resolve => setImmediate(resolve));
    await f.quit();
    assert.deepEqual(f.order, ['prevent', 'POST', 'backend', 'prevent']);
    f.finish();
    await first;
    assert.deepEqual(f.order, ['prevent', 'POST', 'backend', 'prevent', 'stop', 'quit']);
    await f.quit();
    assert.equal(f.order.filter(x => x === 'prevent').length, 2);
});

test('risky work blocks quit before any process is stopped', async () => {
    const f = fixture({allowed: false});
    await f.quit();
    assert.deepEqual(f.order, ['prevent', 'POST', 'focus', 'restore']);
    assert.equal(f.context.isQuitting, false);
});

test('a check timeout blocks instead of forcing and cancels a late admission seal', async () => {
    const f = fixture({unavailable: true});
    await f.quit();
    assert.deepEqual(f.order, ['prevent', 'POST', 'DELETE', 'focus', 'unavailable']);
});

test('desktop Python installation blocks before backend exists', async () => {
    const f = fixture({setup: true});
    f.context.serverProc = null;
    await f.quit();
    assert.deepEqual(f.order, ['prevent', 'focus', 'installation']);
});

test('update install uses the same admission and ES cleanup', async () => {
    const f = fixture();
    assert.equal(await f.context.performShutdown(true), true);
    assert.deepEqual(f.order, ['POST', 'installing', 'backend', 'stop', 'install']);
    const blocked = fixture({allowed: false});
    assert.equal(await blocked.context.performShutdown(true), false);
    assert.deepEqual(blocked.order, ['POST', 'focus', 'restore']);
});

test('activation can focus the existing window during foreground shutdown', () => {
    const restore = source.slice(source.indexOf('function restoreAndFocusMainWindow()'), source.indexOf('function focusActiveWebContents()'));
    let shown = false;
    const context = vm.createContext({isQuitting: true, mainWindow: {
        isDestroyed: () => false, isMinimized: () => false,
        show: () => {shown = true;}, focus() {},
    }, focusActiveWebContents() {}});
    vm.runInContext(restore + '\nrestoreAndFocusMainWindow();', context);
    assert.equal(shown, true);
});

test('managed model cleanup kills Windows trees and Unix process groups', () => {
    for (const isWindows of [true, false]) {
        const commands = [];
        const context = vm.createContext({
            platform: {isWindows}, INSTALL_DIR: '/fake', path,
            fs: {existsSync: name => name.endsWith('llama-swap.pid'), readFileSync: () => '321'},
            execFileSync: (command, args) => {commands.push([command, args]); return 'llama-swap';},
            spawnSync: () => ({status: 0, stdout: '321 llama-swap'}),
            process: {kill: (...args) => commands.push(args)}, log() {},
        });
        vm.runInContext(source.slice(source.indexOf('function forceStopManagedModelRuntimes('), source.indexOf('function backendIsRunning()')), context);
        context.forceStopManagedModelRuntimes();
        if (isWindows) assert.deepEqual(Array.from(commands[1][1]), ['/PID', '321', '/T', '/F']);
        else assert.deepEqual(commands, [[-321, 'SIGKILL']]);
    }
});

test('approved shutdown kills Python immediately without a grace timer', async () => {
    const {EventEmitter} = require('node:events');
    for (const isWindows of [false, true]) {
        const order = [];
        const child = new EventEmitter();
        Object.assign(child, {pid: 123, exitCode: null, signalCode: null, kill: signal => {
            order.push(signal);
            queueMicrotask(() => child.emit('exit'));
            return true;
        }});
        const context = vm.createContext({serverProc: child, platform: {isWindows},
            forceStopManagedModelRuntimes: () => order.push('models'), log() {},
            execFileSync: (command, args) => {order.push(command, Array.from(args)); queueMicrotask(() => child.emit('exit'));},
            setTimeout: () => {throw new Error('No grace deadline is allowed');},
        });
        vm.runInContext(source.slice(source.indexOf('function backendIsRunning()'), source.indexOf('function shutdownHeaders(')), context);
        await context.stopLocalRuntimes();
        assert.deepEqual(order, isWindows ? ['models', 'taskkill', ['/PID', '123', '/F']] : ['models', 'SIGKILL']);
    }
});
