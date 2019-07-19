const clang_tools_bin_dir = require('clang-tools-prebuilt');
const path = require('path');
const proc = require('child_process');
const tmp = require('tmp');

const { GITHUB_EVENT_PATH, GITHUB_TOKEN, GITHUB_WORKSPACE } = process.env;
const event = require(GITHUB_EVENT_PATH);
const { repository } = event;
const {
    owner: { login: owner }
} = repository;
const { name: repo } = repository;
const Octokit = require('@octokit/rest');


async function runClangTidy(files) {
    var tmpFile = tmp.fileSync();
    const tools_bin_path = path.join(clang_tools_bin_dir, 'clang-tidy');
    const args = process.argv.slice(2)
        .concat('-export-fixes=' + tmpFile.name)
        .concat(files);
    const child = proc.spawnSync(tools_bin_path, args, {
        stdio: 'inherit',
        cwd: GITHUB_WORKSPACE
    });
    return child.status;
}

async function run() {

    if (!event.pull_request) {
        throw new Error(`Clang-Tidy Action currently only supports pull requests`);
    }

    const octokit = new Octokit({
        auth: GITHUB_TOKEN
    });

    const response = await octokit.pulls.listFiles({
        owner,
        repo,
        pull_number: event.pull_request.number,
        page: 0,
        per_page: 300
    });

    const files = response.data;
    /* regex for c, cc, h, hpp, etc... */
    const pattern = /.*.[c|h](p{2})?/;
    const filenames = files.map(file => file.filename)
        .filter(filename => filename.match(pattern));

    if (filenames.length == 0) {
        console.log("No C/C++ files changed...");
        process.exit(78);
    }

    const exitcode = await runClangTidy(files);
    process.exit(exitcode);
}

run()
    .catch(err => {
        console.error(err);
        process.exit(1);
    });
