const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {startDockerElasticsearch} = require("../elasticsearch-startup");

test("restarts the stopped container created by the bundled compose file", () => {
    const compose = fs.readFileSync(path.join(__dirname, "../../app/docker-compose.yml"), "utf8");
    const name = compose.match(/container_name:\s*(\S+)/)[1];
    const calls = [];
    const execute = (command, args) => {
        assert.equal(command, "docker");
        calls.push(args);
        if (args[0] === "ps") return name;
        if (args[0] === "inspect") return "false";
        return name;
    };
    assert.equal(startDockerElasticsearch({}, () => {}, execute), true);
    assert.deepEqual(calls.at(-1), ["start", name]);
});

test("does not restart a running container or create a missing container", () => {
    for (const names of ["vyact-es", "", "elasticsearch-other"]) {
        const execute = (_, args) => {
            assert.notEqual(args[0], "start");
            return args[0] === "ps" ? names : "true";
        };
        assert.equal(startDockerElasticsearch({}, () => {}, execute), names === "vyact-es");
    }
});

test("failed restart records stderr and container diagnostics", () => {
    const logs = [];
    const execute = (_, args) => {
        if (args[0] === "ps") return "vyact-es";
        if (args[0] === "start") throw Object.assign(new Error("exit 1"), {stderr: "port already allocated"});
        if (args[0] === "logs") return "startup failure";
        return args.includes("{{.State.Running}}") ? "false" : '{"OOMKilled":true}';
    };
    assert.equal(startDockerElasticsearch({}, message => logs.push(message), execute), false);
    assert.match(logs.join("\n"), /port already allocated/);
    assert.match(logs.join("\n"), /OOMKilled/);
    assert.match(logs.join("\n"), /startup failure/);
});
