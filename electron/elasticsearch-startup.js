const {spawnSync} = require("child_process");

const ELASTICSEARCH_CONTAINER_NAME = "vyact-es";

function executeDocker(command, args, options) {
    const result = spawnSync(command, args, {...options, windowsHide: true});
    if (result.error || result.status !== 0) {
        throw Object.assign(result.error || new Error(`Docker exited with ${result.status}`), {
            stdout: result.stdout, stderr: result.stderr,
        });
    }
    // Elasticsearch writes many startup failures to stderr even when
    // `docker logs` itself exits successfully.
    return (result.stdout || "") + (result.stderr || "");
}

function dockerCommand(args, env, execute = executeDocker) {
    return execute("docker", args, {env, encoding: "utf8", timeout: 10000}).trim();
}

function logElasticsearchDiagnostics(env, log, execute = executeDocker) {
    for (const args of [
        ["inspect", "--format", "{{json .State}}", ELASTICSEARCH_CONTAINER_NAME],
        ["logs", "--tail", "100", ELASTICSEARCH_CONTAINER_NAME],
    ]) {
        try {
            log(`Elasticsearch diagnostic (${args[0]}): ${dockerCommand(args, env, execute)}`);
        } catch (error) {
            log(`Elasticsearch diagnostic failed: ${error.message}\n${error.stdout || ""}\n${error.stderr || ""}`);
        }
    }
}

function startDockerElasticsearch(env, log, execute = executeDocker) {
    try {
        const containers = dockerCommand([
            "ps", "-a", "--filter", `name=^/${ELASTICSEARCH_CONTAINER_NAME}$`,
            "--format", "{{.Names}}",
        ], env, execute).split(/\r?\n/);
        if (!containers.includes(ELASTICSEARCH_CONTAINER_NAME)) {
            log("Vyact Elasticsearch container not found; setup wizard will configure it");
            return false;
        }
        const running = dockerCommand([
            "inspect", "--format", "{{.State.Running}}", ELASTICSEARCH_CONTAINER_NAME,
        ], env, execute);
        if (running !== "true") {
            log(`Starting ${ELASTICSEARCH_CONTAINER_NAME}`);
            dockerCommand(["start", ELASTICSEARCH_CONTAINER_NAME], env, execute);
        }
        return true;
    } catch (error) {
        log(`Elasticsearch start failed: ${error.message}\n${error.stdout || ""}\n${error.stderr || ""}`);
        logElasticsearchDiagnostics(env, log, execute);
        return false;
    }
}

module.exports = {startDockerElasticsearch, logElasticsearchDiagnostics};
