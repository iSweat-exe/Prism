// Based on https://pm2.keymetrics.io/docs/usage/application-declaration/

const os = require("os");

module.exports = {
  apps: [
    {
      name: "prism-api",
      script: "main.py",
      interpreter: `${os.homedir()}/prism/.venv/bin/python`,

      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,

      env: {
        PYTHONUNBUFFERED: "1",
      },

      out_file: "/var/log/prism/out.log",
      error_file: "/var/log/prism/error.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      merge_logs: true,
    },
  ],
};