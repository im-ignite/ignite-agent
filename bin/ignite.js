#!/usr/bin/env node

/**
 * 🔥 IGNITE V3 PRO — CLI Binary Wrapper for npm
 * Launches the autonomous Python agent cleanly cross-platform.
 */

const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

function findPython() {
  const candidates = process.platform === 'win32'
    ? ['python', 'py', 'python3']
    : ['python3', 'python'];

  for (const cmd of candidates) {
    try {
      execSync(`${cmd} --version`, { stdio: 'ignore' });
      return cmd;
    } catch (e) {}
  }
  return null;
}

const pythonCmd = findPython();
if (!pythonCmd) {
  console.error('\n\x1b[1;91m❌ Python 3 is required to run IGNITE but was not found on your PATH.\x1b[0m');
  console.error('Please install Python 3.10+ from: \x1b[1;96mhttps://www.python.org/downloads/\x1b[0m\n');
  process.exit(1);
}

// Ensure openai and rich packages are installed
try {
  execSync(`${pythonCmd} -c "import openai"`, { stdio: 'ignore' });
} catch (e) {
  console.log('\n\x1b[1;33m⚡ First-time launch: Installing required AI packages (openai, rich)...\x1b[0m');
  try {
    execSync(`${pythonCmd} -m pip install openai rich`, { stdio: 'inherit' });
    console.log('\x1b[1;92m✔ Dependencies installed successfully!\x1b[0m\n');
  } catch (err) {
    console.warn('\x1b[33mWarning: Automatic pip install was interrupted. If IGNITE errors, run: pip install openai rich\x1b[0m\n');
  }
}

const agentScript = path.join(__dirname, '..', 'ignite_agent.py');
const args = [agentScript, ...process.argv.slice(2)];

const child = spawn(pythonCmd, args, {
  stdio: 'inherit',
  env: process.env,
  shell: false
});

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
  } else {
    process.exit(code || 0);
  }
});
