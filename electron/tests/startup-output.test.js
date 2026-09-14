const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../main.js'), 'utf8');
const outputHandler = source.slice(source.indexOf('    const pendingServerOutput ='), source.indexOf('    serverProc.stdout.setEncoding'));

test('startup timing survives split chunks without duplicating normal Python logs', () => {
    const saved = [];
    const displayed = [];
    const statuses = [];
    const context = vm.createContext({
        log: line => {saved.push(line); displayed.push(line);},
        sendLoadingLog: line => displayed.push(line),
        sendLoadingStatus: value => statuses.push(value),
        getStartupTranslation: () => ({preparingModels: 'models'}),
        console: {log() {}, error() {}},
    });
    vm.runInContext(outputHandler + '\nthis.forward = forwardServerOutput;', context);
    context.forward('[startup-ti', true);
    context.forward('ordinary stdout\n');
    context.forward('ming] stage=python.entry\r\n[startup-status] models\npartial', true);
    context.forward('', true, true);
    assert.deepEqual(saved, ['[startup-timing] stage=python.entry']);
    assert.deepEqual(displayed, ['ordinary stdout', '[startup-timing] stage=python.entry', '[startup-status] models', 'partial']);
    assert.deepEqual(statuses, ['models']);
});
