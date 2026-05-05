import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const checks = [
  { route: "Today", files: ["src/app/page.tsx", "src/app/actions.ts"], terms: ["Today", "listTodayActions", "saveJobAlert", "skipJobAlert"] },
  { route: "Companies", file: "src/app/companies/page.tsx", terms: ["Companies", "listCompanies", "AddCompanyForm"] },
  { route: "Jobs", file: "src/app/jobs/page.tsx", terms: ["Jobs", "listJobs", "strong_fit_first"] },
  { route: "Profile", files: ["src/app/profile/page.tsx", "src/app/profile/actions.ts"], terms: ["Profile", "getProfile", "importResumeToProfile"] },
  { route: "Applications", files: ["src/app/applications/page.tsx", "src/app/applications/actions.ts"], terms: ["Applications", "listApplications", "generateApplicationTailoringArtifacts"] },
  { route: "Agents", file: "src/app/agents/page.tsx", terms: ["Agents", "listAgentRuns", "Approval queue"] },
  { route: "Analytics", file: "src/app/analytics/page.tsx", terms: ["Analytics", "getAnalyticsOverview", "Weekly review"] },
  { route: "Settings", file: "src/app/settings/page.tsx", terms: ["Settings", "ExportPanel", "ImportWorkspacePanel", "DeletePersonalDataPanel"] },
];

const failures = [];

for (const check of checks) {
  const files = check.files ?? [check.file];
  let source = "";
  for (const file of files) {
    const filePath = join(root, file);
    if (!existsSync(filePath)) {
      failures.push(`${check.route}: missing ${file}`);
      continue;
    }
    source += `\n${readFileSync(filePath, "utf8")}`;
  }
  for (const term of check.terms) {
    if (!source.includes(term)) {
      failures.push(`${check.route}: expected term "${term}" in ${files.join(", ")}`);
    }
  }
}

const shell = readFileSync(join(root, "src/components/shell/app-shell.tsx"), "utf8");
for (const label of ["Today", "Companies", "Jobs", "Applications", "Agents", "Analytics", "Profile", "Settings"]) {
  if (!shell.includes(`label: "${label}"`)) {
    failures.push(`App shell: missing nav label ${label}`);
  }
}

if (failures.length) {
  console.error("Frontend interaction contract failed:");
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log("Frontend interaction contract passed.");
