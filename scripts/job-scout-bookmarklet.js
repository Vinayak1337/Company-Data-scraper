(async () => {
  const apiBase = prompt("Job Scout API base URL", "http://127.0.0.1:8000/api");
  if (!apiBase) return;

  const itemType = /jobs?|careers?|greenhouse|lever|ashby/i.test(location.href) ? "job" : "unknown";
  const notes = prompt("Notes for Job Scout", "") || "";

  const response = await fetch(`${apiBase.replace(/\/$/, "")}/discovery/inbox`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url: location.href,
      title: document.title,
      item_type: itemType,
      notes,
    }),
  });

  if (!response.ok) {
    alert(`Job Scout save failed: ${response.status}`);
    return;
  }

  alert("Saved to Job Scout inbox.");
})();
