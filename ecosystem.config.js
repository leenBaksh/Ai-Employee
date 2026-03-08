/**
 * PM2 Ecosystem Config — AI Employee (Local / WSL2)
 *
 * Manages all watcher processes as persistent daemons.
 * PM2 auto-restarts on crash and survives SSH/TTY disconnects.
 *
 * Quick start:
 *   npm install -g pm2
 *   pm2 start ecosystem.config.js
 *   pm2 save                    # persist list across reboots
 *   pm2 startup                 # hook into OS init (follow printed command)
 *
 * Day-to-day:
 *   pm2 status                  # see all process states
 *   pm2 logs                    # tail all logs
 *   pm2 logs orchestrator       # tail one process
 *   pm2 restart all             # rolling restart
 *   pm2 stop ai-employee-watchdog
 *
 * Profile flags:
 *   --only orchestrator         # start just one process
 *   pm2 start ecosystem.config.js --only orchestrator,scheduler
 *
 * WSL2 note: run `pm2 startup` and follow the printed systemctl command.
 * Requires WSL2 systemd enabled (/etc/wsl.conf: [boot] systemd=true).
 */

const PROJ = "/mnt/d/Hackathon-00/Ai-Employee";
const UV   = `${process.env.HOME}/.local/bin/uv`;

module.exports = {
  apps: [
    // ── Master Orchestrator (manages child watchers internally) ────────────────
    {
      name:          "orchestrator",
      script:        UV,
      args:          "run python orchestrator.py --no-gmail --no-linkedin --no-social",
      cwd:           PROJ,
      interpreter:   "none",      // UV is the executable, not python
      restart_delay: 5000,        // ms before restart after crash
      max_restarts:  10,
      min_uptime:    "10s",       // don't count as crashed if exits within 10s
      watch:         false,
      env: {
        VAULT_PATH: `${PROJ}/AI_Employee_Vault`,
        DRY_RUN:    "false",
      },
      log_file:      `${PROJ}/logs/pm2-orchestrator.log`,
      error_file:    `${PROJ}/logs/pm2-orchestrator-error.log`,
      time:          true,
    },

    // ── Scheduler (cron jobs: daily briefing, weekly audit, SLA monitor) ───────
    {
      name:          "scheduler",
      script:        UV,
      args:          "run scheduler",
      cwd:           PROJ,
      interpreter:   "none",
      restart_delay: 10000,
      max_restarts:  5,
      min_uptime:    "30s",
      watch:         false,
      env: {
        VAULT_PATH: `${PROJ}/AI_Employee_Vault`,
        DRY_RUN:    "false",
      },
      log_file:      `${PROJ}/logs/pm2-scheduler.log`,
      error_file:    `${PROJ}/logs/pm2-scheduler-error.log`,
      time:          true,
    },

    // ── Watchdog (monitors orchestrator PID, restarts on crash) ────────────────
    {
      name:          "ai-employee-watchdog",
      script:        UV,
      args:          "run watchdog-service",
      cwd:           PROJ,
      interpreter:   "none",
      restart_delay: 15000,       // give orchestrator time to start before watchdog checks
      max_restarts:  20,
      watch:         false,
      env: {
        VAULT_PATH: `${PROJ}/AI_Employee_Vault`,
      },
      log_file:      `${PROJ}/logs/pm2-watchdog.log`,
      error_file:    `${PROJ}/logs/pm2-watchdog-error.log`,
      time:          true,
    },

    // ── Gmail Watcher (requires gmail_token.json in secrets/) ──────────────────
    // Uncomment when Gmail credentials are configured.
    // {
    //   name:          "gmail-watcher",
    //   script:        UV,
    //   args:          "run gmail-watcher",
    //   cwd:           PROJ,
    //   interpreter:   "none",
    //   restart_delay: 30000,     // Gmail API rate limits — wait 30s before retry
    //   max_restarts:  5,
    //   min_uptime:    "60s",
    //   env: {
    //     VAULT_PATH: `${PROJ}/AI_Employee_Vault`,
    //   },
    //   log_file:      `${PROJ}/logs/pm2-gmail-watcher.log`,
    //   error_file:    `${PROJ}/logs/pm2-gmail-watcher-error.log`,
    //   time:          true,
    // },
  ],
};
