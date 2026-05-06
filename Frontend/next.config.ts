import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

const frontendDir = dirname(fileURLToPath(import.meta.url));
const setupMarker = resolve(frontendDir, "..", ".jobscout", "setup.json");
const runtimeCommands = new Set(["dev", "start"]);
const requiresLocalSetup =
  runtimeCommands.has(process.env.npm_lifecycle_event ?? "") ||
  process.argv.slice(2).some((argument) => runtimeCommands.has(argument));

if (
  requiresLocalSetup &&
  process.env.JOBSCOUT_ALLOW_UNINITIALIZED !== "true" &&
  !existsSync(setupMarker)
) {
  throw new Error(
    [
      "Job Scout setup is not complete.",
      "Run ./jobscout init from the repository root before starting the frontend.",
      "For CI-only runtime smoke tests, set JOBSCOUT_ALLOW_UNINITIALIZED=true.",
    ].join("\n"),
  );
}

const nextConfig: NextConfig = {
  /* config options here */
};

export default nextConfig;
