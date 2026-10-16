const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../main.js'), 'utf8');
const supportDeclaration = source.slice(source.indexOf('const APP_UPDATE_SUPPORTED ='), source.indexOf('let mainWindow'));

test('installed Windows and macOS apps and Linux AppImages support updates; dev and deb do not', () => {
    for (const [os, packaged, appImage, expected] of [
        ['windows', true, '', true], ['mac', true, '', true],
        ['linux', true, '/opt/Vyact.AppImage', true], ['linux', true, '', false],
        ['windows', false, '', false], ['mac', false, '', false],
    ]) {
        const context = vm.createContext({app: {isPackaged: packaged},
            platform: {isWindows: os === 'windows', isMac: os === 'mac'},
            process: {env: {APPIMAGE: appImage}}});
        assert.equal(vm.runInContext(`${supportDeclaration}\nAPP_UPDATE_SUPPORTED`, context), expected, os);
    }
});
