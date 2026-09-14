const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../main.js'), 'utf8');
const handler = source.slice(source.indexOf('app.on("before-quit",'), source.indexOf('ipcMain.handle("get-log-path"'));

test('repeated quit requests cannot bypass backend and ES cleanup', async () => {
    let beforeQuit;
    let finishBackend;
    const order = [];
    const context = vm.createContext({
        BrowserWindow: {getAllWindows: () => [{isDestroyed: () => false, hide: () => order.push('hide')}]},
        isQuitting: false, shutdownComplete: false, elasticsearchStartPromise: Promise.resolve(),
        stopLocalRuntimes: () => new Promise(resolve => { finishBackend = resolve; order.push('backend'); }),
        runElasticsearchLifecycle: async action => order.push(action), log: () => {},
        app: {on: (_, callback) => {beforeQuit = callback;}, quit: () => order.push('quit')},
    });
    vm.runInContext(handler, context);
    let prevented = 0;
    const event = {preventDefault: () => {prevented++;}};
    const first = beforeQuit(event);
    await new Promise(resolve => setImmediate(resolve));
    await beforeQuit(event);
    assert.equal(prevented, 2);
    assert.deepEqual(order, ['hide', 'backend']);
    finishBackend();
    await first;
    assert.deepEqual(order, ['hide', 'backend', 'stop', 'quit']);
    await beforeQuit(event);
    assert.equal(prevented, 2);
});

test('activation cannot reopen the window during background shutdown', () => {
    const restore = source.slice(source.indexOf('function restoreAndFocusMainWindow()'), source.indexOf('function focusActiveWebContents()'));
    let shown = false;
    const context = vm.createContext({isQuitting: true, mainWindow: {
        isDestroyed: () => false, isMinimized: () => false,
        show: () => {shown = true;}, focus() {},
    }, focusActiveWebContents() {}});
    vm.runInContext(restore + '\nrestoreAndFocusMainWindow();', context);
    assert.equal(shown, false);
});
