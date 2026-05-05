import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const failures = [];

const shell = readFileSync(join(root, "src/components/shell/app-shell.tsx"), "utf8");
for (const expected of ["<main", "aria-label=\"Primary\"", "aria-label=\"Workspace\"", "aria-label=\"Mobile\""]) {
  if (!shell.includes(expected)) {
    failures.push(`App shell missing ${expected}`);
  }
}

const settingsPanels = readFileSync(join(root, "src/components/settings/settings-panels.tsx"), "utf8");
for (const control of ["Watchlist JSON", "Workspace export JSON", "Confirmation phrase", "Quiet hours", "Digest"]) {
  if (!settingsPanels.includes(control)) {
    failures.push(`Settings controls missing visible label: ${control}`);
  }
}

const routeFiles = [
  "src/app/page.tsx",
  "src/app/companies/page.tsx",
  "src/app/jobs/page.tsx",
  "src/app/profile/page.tsx",
  "src/app/applications/page.tsx",
  "src/app/agents/page.tsx",
  "src/app/analytics/page.tsx",
  "src/app/settings/page.tsx",
];

for (const file of routeFiles) {
  const source = readFileSync(join(root, file), "utf8");
  if (!source.includes("PageHeader")) {
    failures.push(`${file} should expose a PageHeader for screen-reader page context.`);
  }
}

if (failures.length) {
  console.error("Frontend accessibility contract failed:");
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log("Frontend accessibility contract passed.");
