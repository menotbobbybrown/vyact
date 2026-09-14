const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// Exercise the actual pre-backend orchestration without loading an Electron GUI.
const source = fs.readFileSync(path.join(__dirname, '../main.js'), 'utf8');
const helpers = source.slice(source.indexOf('async function runElasticsearchLifecycle('), source.indexOf('// ── 서버 시작'));
function createHarness(runCommand) {
    const context = vm.createContext({
        BUNDLED_PYTHON: '/bundled/python', APP_RES: '/resources/app', ES_SESSION: 'session', ES_PORT: 9251,
        path, runCommand, getDockerEnv: () => ({VYACT_INSTALL_DIR: '/existing/data'}),
        log: () => {}, getStartupTranslation: () => ({elasticsearchStarting: 'preparing', elasticsearchWaiting: 'waiting'}),
        sendLoadingStatus: () => {}, setTimeout: callback => callback(), isQuitting: false,
    });
    vm.runInContext(helpers, context);
    return context;
}

test('pre-backend helper uses bundled Python and shares session and original data directory', async () => {
    const calls = [];
    const context = createHarness(async (...args) => { calls.push(args); return ''; });
    await context.runElasticsearchLifecycle('start');
    await context.runElasticsearchLifecycle('stop');
    assert.equal(calls[0][0], '/bundled/python');
    assert.equal(calls[0][1][0], '/resources/app/services/es_lifecycle.py');
    assert.equal(calls[0][2].env.VYACT_INSTALL_DIR, '/existing/data');
    assert.equal(calls[0][2].env.VYACT_ES_SESSION, calls[1][2].env.VYACT_ES_SESSION);
    assert.equal(calls[1][1][1], 'stop');
});

test('Docker starting at login is retried before backend startup', async () => {
    let attempts = 0;
    const context = createHarness(async () => {
        if (++attempts < 3) throw Object.assign(new Error('Docker offline'), {exitCode: 2});
        return '';
    });
    await context.startElasticsearchForDesktop();
    assert.equal(attempts, 3);
});

test('ambiguous storage errors are not retried or silently switched', async () => {
    let attempts = 0;
    const context = createHarness(async () => {
        attempts++;
        throw Object.assign(new Error('ambiguous storage'), {exitCode: 1});
    });
    await assert.rejects(context.startElasticsearchForDesktop(), /ambiguous storage/);
    assert.equal(attempts, 1);
});

test('Docker wait is bounded', async () => {
    let attempts = 0;
    const context = createHarness(async () => {
        attempts++;
        throw Object.assign(new Error('Docker offline'), {exitCode: 2});
    });
    await assert.rejects(context.startElasticsearchForDesktop(), /Docker offline/);
    assert.equal(attempts, 30);
});

test('quitting cancels subsequent startup retries', async () => {
    let attempts = 0;
    const context = createHarness(async () => {
        attempts++;
        context.isQuitting = true;
        throw Object.assign(new Error('Docker offline'), {exitCode: 2});
    });
    await context.startElasticsearchForDesktop();
    assert.equal(attempts, 1);
});
