const API_BASE = 'http://127.0.0.1:8000';

const els = {
  statusText: document.getElementById('statusText'),
  totalJobs: document.getElementById('totalJobs'),
  failedJobs: document.getElementById('failedJobs'),
  runningJobs: document.getElementById('runningJobs'),
  workers: document.getElementById('workers'),
  queueList: document.getElementById('queueList'),
  jobList: document.getElementById('jobList'),
  workerList: document.getElementById('workerList'),
  notice: document.getElementById('notice'),
  queueForm: document.getElementById('queueForm'),
  jobForm: document.getElementById('jobForm'),
  refreshBtn: document.getElementById('refreshBtn')
};

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || 'Request failed');
  }
  return response.json();
}

function showNotice(message) {
  els.notice.textContent = message;
  els.notice.classList.add('show');
  setTimeout(() => els.notice.classList.remove('show'), 3000);
}

function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  return date.toLocaleString();
}

function renderDashboard(data) {
  els.totalJobs.textContent = data.total_jobs ?? 0;
  els.failedJobs.textContent = data.failed_jobs ?? 0;
  els.runningJobs.textContent = data.running_jobs ?? 0;
  els.workers.textContent = data.online_workers ?? 0;
  els.statusText.textContent = `Live • ${data.queue_sizes?.length || 0} queue(s)`;
}

function renderQueues(queues) {
  if (!queues.length) {
    els.queueList.innerHTML = '<div class="queue-item"><strong>No queues yet</strong><div class="meta">Create one to start routing jobs.</div></div>';
    return;
  }

  els.queueList.innerHTML = queues.map((queue) => `
    <div class="queue-item">
      <strong>${queue.name}</strong>
      <div class="meta">Priority: ${queue.priority} • Concurrency: ${queue.concurrency}</div>
      <div class="stats-row">
        <span class="chip">Pending ${queue.pending}</span>
        <span class="chip ok">Running ${queue.running}</span>
        <span class="chip">Completed ${queue.completed}</span>
        <span class="chip danger">Failed ${queue.failed}</span>
      </div>
    </div>
  `).join('');
}

function renderJobs(jobs) {
  if (!jobs.length) {
    els.jobList.innerHTML = '<div class="job-item"><strong>No jobs yet</strong><div class="meta">Submit a job to see it appear here.</div></div>';
    return;
  }

  els.jobList.innerHTML = jobs.slice(0, 8).map((job) => `
    <div class="job-item">
      <strong>${job.queue_name}</strong>
      <div class="meta">${job.payload?.to || job.payload?.subject || 'Job payload'}</div>
      <div class="stats-row">
        <span class="chip ${job.status === 'completed' ? 'ok' : job.status === 'dead_letter' ? 'danger' : 'warn'}">${job.status}</span>
        <span class="chip">Attempts ${job.attempts}</span>
        <span class="chip">${formatDate(job.created_at)}</span>
      </div>
    </div>
  `).join('');
}

function renderWorkers(workers) {
  if (!workers.length) {
    els.workerList.innerHTML = '<div class="worker-item"><strong>No workers online</strong><div class="meta">Register a worker to start processing.</div></div>';
    return;
  }

  els.workerList.innerHTML = workers.map((worker) => `
    <div class="worker-item">
      <strong>${worker.name}</strong>
      <div class="meta">Heartbeat: ${formatDate(worker.last_heartbeat)}</div>
      <div class="stats-row">
        <span class="chip ${worker.online ? 'ok' : 'danger'}">${worker.online ? 'Online' : 'Offline'}</span>
      </div>
    </div>
  `).join('');
}

async function loadData(options = { silent: false }) {
  try {
    const [dashboard, queues, jobs, workers] = await Promise.all([
      fetchJson(`${API_BASE}/dashboard`),
      fetchJson(`${API_BASE}/queues`),
      fetchJson(`${API_BASE}/jobs`),
      fetchJson(`${API_BASE}/workers`)
    ]);

    renderDashboard(dashboard);
    renderQueues(queues);
    renderJobs(jobs);
    renderWorkers(workers);

    if (!options.silent) {
      els.statusText.textContent = `Live • ${dashboard.queue_sizes?.length || 0} queue(s)`;
    }
  } catch (error) {
    if (!options.silent) {
      showNotice(`Unable to reach API: ${error.message}`);
    }
  }
}

els.queueForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const data = new FormData(els.queueForm);

  try {
    await fetchJson(`${API_BASE}/queues`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: data.get('queueName'),
        priority: data.get('priority'),
        concurrency: Number(data.get('concurrency')),
        retries: Number(data.get('retries')),
        backoff: data.get('backoff'),
        paused: data.get('paused') === 'on'
      })
    });
    els.queueForm.reset();
    showNotice('Queue created successfully.');
    await loadData({ silent: true });
  } catch (error) {
    showNotice(error.message);
  }
});

els.jobForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const data = new FormData(els.jobForm);

  try {
    await fetchJson(`${API_BASE}/jobs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        queue_name: data.get('queueName'),
        payload: {
          to: data.get('to'),
          subject: data.get('subject'),
          body: data.get('body')
        },
        job_type: data.get('jobType'),
        delay_seconds: Number(data.get('delay')) || 0,
        scheduled_for: data.get('scheduledFor') || null,
        recurring: data.get('recurring') === 'on'
      })
    });
    els.jobForm.reset();
    showNotice('Job submitted successfully.');
    await loadData({ silent: true });
  } catch (error) {
    showNotice(error.message);
  }
});

els.refreshBtn.addEventListener('click', loadData);

window.addEventListener('DOMContentLoaded', () => {
  loadData();
  setInterval(loadData, 10000);
});
