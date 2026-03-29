const totalUsersEl = document.getElementById('total-users');
const totalHitsEl = document.getElementById('total-hits');
const successHitsEl = document.getElementById('success-hits');
const adminReqList = document.getElementById('admin-req-list');

const newReqId = document.getElementById('new-req-id');
const newReqUrl = document.getElementById('new-req-url');
const newReqName = document.getElementById('new-req-name');
const addReqBtn = document.getElementById('add-req-btn');

window.onload = async () => {
    await fetchStats();
    await fetchRequirements();
};

async function fetchStats() {
    try {
        const res = await fetch('/api/admin/stats');
        const data = await res.json();
        if (data.success) {
            totalUsersEl.innerText = data.stats.total_users || 0;
            totalHitsEl.innerText = data.stats.total_hits || 0;
            successHitsEl.innerText = data.stats.success_hits || 0;
        } else {
            alert("Unauthorized! Redirecting...");
            window.location.href = '/';
        }
    } catch (e) {
        console.error("Stats fetch failed", e);
    }
}

async function fetchRequirements() {
    try {
        const res = await fetch('/api/admin/requirements');
        const data = await res.json();
        if (data.success) {
            renderRequirements(data.requirements);
        }
    } catch (e) {
        console.error("Requirements fetch failed", e);
    }
}

function renderRequirements(reqs) {
    if (!reqs || reqs.length === 0) {
        adminReqList.innerHTML = '<p style="font-size:12px; color:var(--text-dim); text-align:center;">No requirements added.</p>';
        return;
    }
    adminReqList.innerHTML = reqs.map(req => `
        <div class="req-item-admin">
            <div>
                <div style="font-size:13px; font-weight:600;">${req.name}</div>
                <div style="font-size:10px; color:var(--text-dim);">${req.chat_id}</div>
            </div>
            <button class="btn-delete" onclick="deleteReq('${req.chat_id}')">✕</button>
        </div>
    `).join('');
}

addReqBtn.onclick = async () => {
    const id = newReqId.value.trim();
    const url = newReqUrl.value.trim();
    const name = newReqName.value.trim();
    
    if (!id || !url || !name) return alert("Please fill all fields!");
    
    try {
        const res = await fetch('/api/admin/requirements', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: id, url: url, name: name })
        });
        const data = await res.json();
        if (data.success) {
            newReqId.value = ''; newReqUrl.value = ''; newReqName.value = '';
            await fetchRequirements();
            alert("Requirement added!");
        }
    } catch (e) { }
};

async function deleteReq(chatId) {
    if (!confirm("Are you sure?")) return;
    try {
        await fetch(`/api/admin/requirements?chat_id=${chatId}`, { method: 'DELETE' });
        await fetchRequirements();
    } catch (e) { }
}
