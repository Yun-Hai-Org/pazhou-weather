async function triggerGitHubDispatch(env) {
  const { GH_OWNER, GH_REPO, GH_PAT } = env;
  if (!GH_OWNER || !GH_REPO || !GH_PAT) {
    throw new Error("Missing GH_OWNER, GH_REPO, or GH_PAT");
  }
  const url = `https://api.github.com/repos/${GH_OWNER}/${GH_REPO}/dispatches`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${GH_PAT}`,
      "Content-Type": "application/json",
      "User-Agent": "weather-cron-worker",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify({ event_type: "weather-report" }),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`GitHub dispatch failed: ${response.status} ${text}`);
  }
}

export default {
  async scheduled(_event, env, _ctx) {
    await triggerGitHubDispatch(env);
  },
  async fetch(_request, env, _ctx) {
    try {
      await triggerGitHubDispatch(env);
      return new Response("weather-report dispatch triggered", { status: 200 });
    } catch (err) {
      return new Response(String(err), { status: 500 });
    }
  },
};
