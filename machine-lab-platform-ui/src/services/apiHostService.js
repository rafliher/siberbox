import api from './api';

export function listHost() {
  return api.get('/hosts/');
}

export function registerHost(hostData) {
  return api.post('/hosts/', hostData);
}

export function getHostStatus(hostId) {
  return api.get(`/hosts/${hostId}/status`);
}

export function updateHost(hostId, updateData) {
  return api.patch(`/hosts/${hostId}`, updateData);
}

export function deleteHost(hostId) {
  return api.delete(`/hosts/${hostId}`);
}

export function heartBeat(hostId) {
  return api.post(`/hosts/${hostId}/heartbeat`);
}