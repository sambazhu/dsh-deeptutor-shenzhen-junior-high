#!/usr/bin/env node
/**
 * One-shot profile installer for the dsh-deeptutor bundle.
 *
 * Wraps `dsh plugin --profile <name> add dsh-deeptutor` and works around the
 * pnpm workspace-root check: the dsh profile scaffold always writes a
 * `pnpm-workspace.yaml`, which makes the profile directory a pnpm workspace
 * root, so on pnpm >= 8 `pnpm add` aborts with ERR_PNPM_ADDING_TO_ROOT unless
 * the explicit `-w`/`--workspace-root` flag is passed. The plain command is
 * tried first (older pnpm versions / older dsh templates don't need the
 * flag), and when the check trips the installer retries with the correct
 * flag automatically — one command that works on any setup.
 *
 * Usage:
 *   node scripts/install-profile.mjs [--profile <name>]  (from a checkout)
 *   pnpm dlx dsh-deeptutor --profile web                 (published one-liner)
 *
 * Options:
 *   -p, --profile <name>   dsh profile to install into (default: web)
 *   -h, --help             show this help
 *
 * Besides installing the bundle, the installer copies the package's bundled
 * skills (`.agents/skills/deeptutor`, `.agents/skills/html-doc`) into
 * `<DSH_HOME>/skills/<name>/`, where dsh auto-discovers them. Existing files
 * are overwritten; files not shipped by the package are never deleted.
 */
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { delimiter, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const PKG = 'dsh-deeptutor';
const NAME = 'dsh-deeptutor-install';
const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(SCRIPT_DIR, '..');
const SKILLS_DIR = join(REPO_ROOT, '.agents', 'skills');

const USAGE = `usage: dsh-deeptutor [--profile <name>] [--local]

Install the ${PKG} bundle into a dsh profile via \`dsh plugin add\`,
automatically handling the pnpm workspace-root check and Electron desktop profile.

options:
  -p, --profile <name>   dsh profile to install into (default: web)
  -l, --local            install from this local checkout instead of npm registry
  -h, --help             show this help`;

function parseArgs(argv) {
  const out = { profile: 'web', local: false, help: false };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--profile' || arg === '-p') {
      const value = argv[++i];
      if (!value) throw new Error(`${arg} requires a value`);
      out.profile = value;
    } else if (arg === '--local' || arg === '-l') {
      out.local = true;
    } else if (arg === '--help' || arg === '-h') {
      out.help = true;
    } else {
      throw new Error(`unknown argument: ${arg}`);
    }
  }
  if (!/^[A-Za-z0-9_.-]+$/.test(out.profile)) {
    throw new Error(`invalid profile name: ${out.profile} (allowed: letters, digits, . _ -)`);
  }
  return out;
}

/**
 * Locate the dsh CLI. On Windows the shim is usually a .ps1 (sometimes a
 * .cmd/.exe sibling); a plain `spawnSync('dsh', ...)` would not resolve the
 * PowerShell shim, so walk PATH explicitly and fall back to `powershell -File`.
 * Note: with `shell: true` Node does not quote the command itself, so a
 * .cmd/.bat path containing spaces must carry its own quotes.
 */
function resolveDsh() {
  if (process.platform !== 'win32') {
    return { file: 'dsh', args: [], shell: false, describe: 'dsh' };
  }
  const dirs = (process.env.PATH || '').split(delimiter).filter(Boolean);
  for (const dir of dirs) {
    for (const name of ['dsh.exe']) {
      const file = join(dir, name);
      if (existsSync(file)) return { file, args: [], shell: false, describe: file };
    }
    for (const name of ['dsh.cmd', 'dsh.bat']) {
      const file = join(dir, name);
      if (existsSync(file)) {
        return { file: `"${file}"`, args: [], shell: true, describe: file };
      }
    }
    const ps1 = join(dir, 'dsh.ps1');
    if (existsSync(ps1)) {
      return {
        file: 'powershell.exe',
        args: ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', ps1],
        shell: false,
        describe: ps1,
      };
    }
  }
  return null;
}

/**
 * Run `dsh plugin --profile <name> add dsh-deeptutor [flags]`.
 * Both streams are captured (note: pnpm 8 on Windows prints its errors —
 * including ERR_PNPM_ADDING_TO_ROOT — on stdout), so the workspace-root
 * check can be detected programmatically; captured output is replayed on
 * success/failure instead of streamed live.
 */
function runDsh(dsh, profile, pkgSpec, flag) {
  const args = [
    ...dsh.args,
    'plugin',
    '--profile',
    profile,
    'add',
    pkgSpec,
    ...(flag ? ['-w'] : []),
  ];
  return spawnSync(dsh.file, args, {
    shell: dsh.shell,
    stdio: ['inherit', 'pipe', 'pipe'],
    encoding: 'utf8',
  });
}

/**
 * Direct profile install for Electron-managed profiles (e.g. `desktop`, which
 * `dsh plugin --profile desktop` rejects on CLI) or `--local` checkout installs.
 * Mirrors what the Electron app's internal plugin manager does:
 *   1. `pnpm add -w <pkgSpec>` inside `<DSH_HOME>/profiles/<profile>`
 *   2. Ensure `dsh-deeptutor` is listed in `package.json -> dsh.profile.bundles`
 */
function installDirectWithPnpm(profile, pkgSpec) {
  const dshHome = process.env.DSH_HOME || join(homedir(), '.dsh');
  const profileDir = join(dshHome, 'profiles', profile);
  const pkgJsonPath = join(profileDir, 'package.json');
  if (!existsSync(pkgJsonPath)) {
    console.error(`error: profile directory or package.json not found at ${pkgJsonPath}`);
    process.exit(1);
  }
  const pnpmRes = spawnSync('pnpm', ['add', '-w', pkgSpec], {
    cwd: profileDir,
    shell: process.platform === 'win32',
    stdio: 'inherit',
    encoding: 'utf8',
  });
  if (pnpmRes.status !== 0) {
    process.exit(pnpmRes.status ?? 1);
  }
  const pkgJson = JSON.parse(readFileSync(pkgJsonPath, 'utf8'));
  pkgJson.dsh = pkgJson.dsh || {};
  pkgJson.dsh.profile = pkgJson.dsh.profile || {};
  const bundles = Array.isArray(pkgJson.dsh.profile.bundles)
    ? pkgJson.dsh.profile.bundles
    : [];
  if (!bundles.includes(PKG)) {
    bundles.push(PKG);
    pkgJson.dsh.profile.bundles = bundles;
    writeFileSync(pkgJsonPath, JSON.stringify(pkgJson, null, 2) + '\n', 'utf8');
  }
}

const combinedOutput = (result) => `${result.stdout ?? ''}${result.stderr ?? ''}`;

function verifyHint(profile) {
  if (profile === 'desktop') {
    return 'restart the DSH Desktop app and check Settings -> Plugins / Bundles';
  }
  const grep = process.platform === 'win32' ? 'findstr dsh-deeptutor' : 'grep dsh-deeptutor';
  return `dsh --profile ${profile} --dump-config | ${grep}`;
}

function main() {
  let opts;
  try {
    opts = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(`error: ${error.message}\n\n${USAGE}`);
    process.exit(2);
  }
  if (opts.help) {
    console.log(USAGE);
    return;
  }

  const pkgSpec = opts.local ? `file:${REPO_ROOT}` : PKG;

  if (opts.local || opts.profile === 'desktop') {
    installDirectWithPnpm(opts.profile, pkgSpec);
    finish(opts.profile);
    return;
  }

  const dsh = resolveDsh();
  if (!dsh) {
    console.error(`error: cannot find the dsh CLI on PATH — install dsh first, then re-run this installer`);
    process.exit(2);
  }

  // Plain command first; retry with `-w` only when the workspace-root check
  // trips (fresh profiles and pnpm >= 8), or back off `-w` if a previous run
  // left a stray flag in an environment that rejects it.
  let attempt = runDsh(dsh, opts.profile, pkgSpec, false);
  if (attempt.error) {
    console.error(`error: failed to run dsh via ${dsh.describe}: ${attempt.error.message}`);
    process.exit(1);
  }

  if (attempt.status === 0) {
    process.stdout.write(attempt.stdout ?? '');
    finish(opts.profile);
    return;
  }

  const firstOutput = combinedOutput(attempt);
  if (/managed exclusively by the Electron application/i.test(firstOutput)) {
    console.error(`\n${NAME}: profile '${opts.profile}' is Electron-managed — installing directly into ~/.dsh/profiles/${opts.profile} via pnpm...\n`);
    installDirectWithPnpm(opts.profile, pkgSpec);
    finish(opts.profile);
    return;
  }
  let retryFlag = null;
  if (/ERR_PNPM_ADDING_TO_ROOT|workspace root/i.test(firstOutput)) retryFlag = true;
  else if (/may only be used inside a workspace/i.test(firstOutput)) retryFlag = false;

  if (retryFlag !== null) {
    console.error(`\n${NAME}: pnpm flagged the workspace-root check — retrying with ${retryFlag ? '-w' : 'no'} workspace-root flag...\n`);
    const retried = runDsh(dsh, opts.profile, pkgSpec, retryFlag);
    if (retried.error) {
      console.error(`error: failed to run dsh via ${dsh.describe}: ${retried.error.message}`);
      process.exit(1);
    }
    if (retried.status === 0) {
      process.stdout.write(retried.stdout ?? '');
      finish(opts.profile);
      return;
    }
    process.stderr.write(`${firstOutput}\n--- retry output (${retryFlag ? '-w' : 'plain'}) ---\n${combinedOutput(retried)}\n`);
    process.exit(retried.status ?? 1);
  }

  if (/pnpm not found/i.test(firstOutput)) {
    process.stderr.write(`${firstOutput}\n${NAME}: pnpm is required to manage profile plugins — install pnpm and re-run\n`);
  } else {
    process.stderr.write(firstOutput);
  }
  process.exit(attempt.status ?? 1);
}

function finish(profile) {
  const skills = installSkills();
  console.log(`
\u2714 ${PKG} installed into profile '${profile}'
  \u00b7 dependency added and dsh.profile.bundles reconciled (bundle patch auto-registered)${skills}

next steps:
  1. restart dsh  (the bundle list is resolved at boot)
  2. verify:      ${verifyHint(profile)}`);
}

/**
 * Copy the package's bundled skills into <DSH_HOME>/skills/<name>/ (dsh
 * auto-discovers skills there). Existing files are overwritten in place;
 * anything not shipped by this package is left untouched. Returns a
 * human-readable summary line (or '' when there is nothing to install).
 */
function installSkills() {
  if (!existsSync(SKILLS_DIR)) {
    console.error(`\n${NAME}: warning: no .agents/skills/ directory in this package — skill install skipped (old version?)`);
    return '';
  }
  const dshHome = process.env.DSH_HOME || join(homedir(), '.dsh');
  const installed = [];
  for (const entry of readdirSync(SKILLS_DIR, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const src = join(SKILLS_DIR, entry.name);
    const dest = join(dshHome, 'skills', entry.name);
    mkdirSync(dest, { recursive: true });
    cpSync(src, dest, { recursive: true, force: true });
    installed.push(entry.name);
  }
  if (installed.length === 0) return '';
  return `\n  \u00b7 skills installed: ${installed.join(', ')} -> ${join(dshHome, 'skills')}`;
}

main();
