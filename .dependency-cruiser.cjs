/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: "packages-no-import-apps-or-services",
      severity: "error",
      comment: "packages/ is reusable libs — must not depend on app/service layer",
      from: { path: "^packages" },
      to: { path: "^(apps|services)" },
    },
    {
      name: "common-is-the-floor",
      severity: "error",
      comment: "common/ is the lowest layer — must not import upward",
      from: { path: "^common" },
      to: { path: "^(packages|apps|services)" },
    },
    {
      name: "no-circular",
      severity: "error",
      from: {},
      to: { circular: true },
    },
  ],
  options: {
    tsConfig: { fileName: "tsconfig.json" },
    doNotFollow: { path: "node_modules" },
  },
};
