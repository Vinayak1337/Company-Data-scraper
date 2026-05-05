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

const settingsPage = readFileSync(join(root, "src/app/settings/page.tsx"), "utf8");
for (const control of ["Email address", "Minimum match score", "Minimum confidence", "AI", "Notifications"]) {
  if (!settingsPage.includes(control)) {
    failures.push(`Settings controls missing visible label: ${control}`);
  }
}

const routeFiles = [
  "src/app/page.tsx",
  "src/app/companies/page.tsx",
  "src/app/jobs/page.tsx",
  "src/app/profile/page.tsx",
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
