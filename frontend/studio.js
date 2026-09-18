document.getElementById('shell').innerHTML = Aero.shell();
const viewer = document.getElementById('studioCanvas');

async function loadJobs(){
    try {
        const r = await Aero.api('/jobs');
        const completed = r.jobs.filter(j => j.status === 'completed');
        studioJob.innerHTML = completed.length ? completed.map(j => `<option value="${j.job_id}">${j.filename || j.job_id.slice(0,8)}</option>`).join('') : '<option value="">No completed reconstructions</option>';
        if(completed.length) loadJob(studioJob.value);
        else projectMessage.textContent = 'Complete a reconstruction to inspect it here.';
    } catch(e) {
        projectMessage.textContent = e.message;
        Aero.toast(e.message, true);
    }
}

async function loadJob(id){
    if(!id) return;
    viewerState.textContent = 'Loading geometry';
    try {
        const [payload, metrics] = await Promise.all([Aero.api(`/points/${id}`), Aero.api(`/measurements/${id}`)]);
        
        if (payload.glb_url) {
            viewer.setAttribute('environment-image', 'neutral');
            viewer.setAttribute('exposure', '1.5');
            viewer.setAttribute('tone-mapping', 'neutral');
            viewer.setAttribute('shadow-intensity', '0.6');
            viewer.src = `${payload.glb_url}?t=${Date.now()}`;
            viewerEmpty.classList.add('hidden');
            viewer.style.display = 'block';
            viewerState.textContent = 'High-fidelity mesh active';
        } else {
            throw new Error("No textured 3D model available for this job.");
        }
        
        pointCount.textContent = `${(metrics.mesh_triangles || 0).toLocaleString()} triangles`;
        projectMessage.textContent = `Loaded ${id.slice(0,8)} · verified project output`;
        statSparse.textContent = (metrics.sparse_points || 0).toLocaleString();
        statDense.textContent = (metrics.dense_points || 0).toLocaleString();
        statVertices.textContent = (metrics.mesh_vertices || 0).toLocaleString();
        statTriangles.textContent = (metrics.mesh_triangles || 0).toLocaleString();
        statReprojection.textContent = metrics.reprojection_error_px != null ? `${metrics.reprojection_error_px} px` : '—';
        statGsd.textContent = typeof metrics.gsd_cm_px === 'number' ? `${metrics.gsd_cm_px.toFixed(2)} cm/px` : 'Unavailable';
        statCrs.textContent = metrics.crs || 'Local metric';
    } catch(e) {
        viewer.style.display = 'none';
        viewerEmpty.classList.remove('hidden');
        viewerState.textContent = 'Output unavailable';
        projectMessage.textContent = e.message;
    }
}

toggleSpin.onclick = () => {
    const isAuto = viewer.hasAttribute('auto-rotate');
    if (isAuto) viewer.removeAttribute('auto-rotate');
    else viewer.setAttribute('auto-rotate', '');
    toggleSpin.textContent = isAuto ? 'Resume rotation' : 'Pause rotation';
};

resetView.onclick = () => {
    viewer.cameraOrbit = 'auto auto auto';
    viewer.cameraTarget = 'auto auto auto';
};

studioJob.onchange = () => loadJob(studioJob.value);
loadJobs();
