import { API_BASE_URL, postJson } from './client';

export const pipelineApi = {
  trigger: (tasks, date) => postJson(`${API_BASE_URL}/api/v1/pipeline/trigger`, { tasks, date }),
  getStatus: (jobId) => fetch(`${API_BASE_URL}/api/v1/pipeline/status/${jobId}`).then(r => r.json()),
};
