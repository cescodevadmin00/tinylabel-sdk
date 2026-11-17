// Node >=18. Preview only; never prints or opens Bluetooth.
// Usage: node examples/node_bridge.js /absolute/path/to/python label.png
const { spawn } = require("node:child_process");
const path = require("node:path");

function invoke(pythonExecutable, args) {
  return new Promise((resolve, reject) => {
    const process = spawn(pythonExecutable, ["-m", "tinylabel_sdk", ...args], {
      shell: false,
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "", stderr = "";
    process.stdout.setEncoding("utf8");
    process.stderr.setEncoding("utf8");
    process.stdout.on("data", data => { stdout += data; });
    process.stderr.on("data", data => { stderr += data; });
    process.once("error", reject);
    process.once("close", code => {
      if (code !== 0) return reject(new Error(`CLI exited ${code}: ${stderr || stdout}`));
      try { resolve(JSON.parse(stdout)); } catch (error) { reject(error); }
    });
  });
}

module.exports = { invoke };
if (require.main === module) {
  const [pythonExecutable, image] = process.argv.slice(2);
  if (!pythonExecutable || !image) {
    console.error("Usage: node examples/node_bridge.js PYTHON_EXECUTABLE IMAGE");
    process.exitCode = 2;
  } else {
    invoke(pythonExecutable, ["preview", path.resolve(image), "--out", path.resolve("preview")])
      .then(result => console.log(JSON.stringify(result, null, 2)))
      .catch(error => { console.error(error.message); process.exitCode = 1; });
  }
}

// For an authorized print, pass the entire batch in one invocation, a durable
// --job-id and --journal, the exact --target, and --aligned only after the
// operator acknowledgment. Code 0 + transmitted_unconfirmed is not delivery.
// Do not automatically kill/retry a print process on an HTTP request timeout.
