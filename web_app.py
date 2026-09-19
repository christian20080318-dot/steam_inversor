import http.server
import socketserver
import json
import urllib.parse
import os
import sys
import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from database import (
    get_connection, 
    get_current_capital, 
    process_user_decision, 
    get_today_aggressive_count,
    update_real_wallet_balance
)
from config import CURRENCY_SYMBOL, INITIAL_CAPITAL
from steam_auth import steam_auth_mgr

PORT = int(os.getenv("PORT", 8080))

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SteamVault Pro — Centro de Inversión y Arbitraje Steam</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        steamDark: '#101822',
                        steamCard: '#172435',
                        steamCardHover: '#1f3148',
                        steamAccent: '#66c0f4',
                        steamBlue: '#1b2838',
                        steamGreen: '#00ff88',
                        steamOrange: '#ff9900'
                    }
                }
            }
        }
    </script>
    <style>
        body {
            background: radial-gradient(circle at top, #1b2838 0%, #0d121a 100%);
            min-height: 100vh;
            color: #e5e7eb;
            font-family: system-ui, -apple-system, sans-serif;
        }
        .glow-accent {
            box-shadow: 0 0 20px rgba(102, 192, 244, 0.15);
        }
    </style>
</head>
<body class="p-4 md:p-8">
    <div class="max-w-7xl mx-auto space-y-6">
        
        <!-- HEADER -->
        <header class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-steamCard p-6 rounded-2xl border border-gray-800 glow-accent">
            <div>
                <div class="flex items-center gap-3">
                    <span class="text-3xl">🎮</span>
                    <h1 class="text-2xl md:text-3xl font-extrabold tracking-wide text-white">
                        STEAM<span class="text-steamAccent">VAULT</span> PRO
                    </h1>
                    <span class="bg-emerald-500/20 text-emerald-400 text-xs px-2.5 py-1 rounded-full font-semibold border border-emerald-500/30">
                        EN VIVO (PEN S/)
                    </span>
                </div>
                <p class="text-gray-400 text-sm mt-1">Plataforma de Arbitraje, Simulador Algorítmico y Gestión de Cartera en Soles</p>
            </div>
            <div class="flex flex-wrap items-center gap-3">
                <div id="steam-status-container" class="flex items-center">
                    <!-- Dinámico: Estado de Steam y botón Vincular -->
                </div>
                <button onclick="refreshData()" class="bg-steamBlue hover:bg-slate-700 text-steamAccent px-4 py-2 rounded-xl text-sm font-semibold border border-steamAccent/30 transition">
                    🔄 Actualizar Datos
                </button>
                <button onclick="openModal('modal-balance')" class="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white px-4 py-2 rounded-xl text-sm font-semibold shadow-lg transition">
                    ✏️ Modificar Mi Cartera
                </button>
            </div>
        </header>

        <!-- STATS CARDS -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            
            <!-- MI CARTERA REAL -->
            <div class="bg-steamCard p-5 rounded-2xl border border-gray-800 relative overflow-hidden">
                <div class="flex justify-between items-center text-gray-400 text-xs font-semibold uppercase tracking-wider">
                    <span>Mi Cartera Real</span>
                    <span class="text-emerald-400">● ACTIVA</span>
                </div>
                <div class="mt-3">
                    <span class="text-3xl font-extrabold text-white" id="real-total">S/ 0.00</span>
                </div>
                <div class="mt-2 text-xs text-gray-400 flex justify-between border-t border-gray-800/80 pt-2">
                    <span>Efectivo: <b class="text-steamAccent" id="real-cash">S/ 0.00</b></span>
                    <span>En Skins/Cajas: <b class="text-amber-400" id="real-inv">S/ 0.00</b></span>
                </div>
            </div>

            <!-- SIMULADOR ESTRATÉGICO S/ 500 -->
            <div class="bg-steamCard p-5 rounded-2xl border border-gray-800">
                <div class="flex justify-between items-center text-gray-400 text-xs font-semibold uppercase tracking-wider">
                    <span>Simulador (S/ 500 Base)</span>
                    <span class="text-purple-400">● VIRTUAL</span>
                </div>
                <div class="mt-3">
                    <span class="text-3xl font-extrabold text-white" id="sim-total">S/ 500.00</span>
                </div>
                <div class="mt-2 text-xs text-gray-400 flex justify-between border-t border-gray-800/80 pt-2">
                    <span>Efectivo: <b class="text-purple-300" id="sim-cash">S/ 500.00</b></span>
                    <span>En Activos: <b class="text-amber-400" id="sim-inv">S/ 0.00</b></span>
                </div>
            </div>

            <!-- GANANCIA NETA REALIZADA -->
            <div class="bg-steamCard p-5 rounded-2xl border border-gray-800">
                <div class="text-gray-400 text-xs font-semibold uppercase tracking-wider">Ganancia Realizada (PnL)</div>
                <div class="mt-3">
                    <span class="text-3xl font-extrabold text-steamGreen" id="total-profit">+S/ 0.00</span>
                </div>
                <div class="mt-2 text-xs text-gray-400 border-t border-gray-800/80 pt-2">
                    Comisión Valve (15%) ya descontada
                </div>
            </div>

            <!-- OPERACIONES AGRESIVAS HOY -->
            <div class="bg-steamCard p-5 rounded-2xl border border-gray-800">
                <div class="flex justify-between items-center text-gray-400 text-xs font-semibold uppercase tracking-wider">
                    <span>Operaciones Agresivas</span>
                    <span class="text-steamOrange font-bold" id="aggressive-badge">0 / 3</span>
                </div>
                <div class="mt-3">
                    <span class="text-2xl font-bold text-white" id="aggressive-text">Límite Diario</span>
                </div>
                <div class="mt-2 text-xs text-gray-400 border-t border-gray-800/80 pt-2">
                    Máximo 3 operaciones de alto riesgo/día
                </div>
            </div>

        </div>

        <!-- GRÁFICO HISTÓRICO DE TENDENCIA -->
        <div class="bg-steamCard p-6 rounded-2xl border border-gray-800">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
                <div>
                    <h2 class="text-xl font-bold text-white">📈 Tendencia Histórica del Portafolio</h2>
                    <p class="text-xs text-gray-400 mt-0.5">Evolución en Soles (PEN) del capital invertido vs. valor total</p>
                </div>
                <div class="flex items-center bg-steamDark p-1 rounded-xl border border-gray-800 text-xs">
                    <button onclick="setChartRange(3)" id="btn-3d" class="px-3 py-1.5 rounded-lg text-gray-400 hover:text-white transition">3 Días</button>
                    <button onclick="setChartRange(7)" id="btn-7d" class="px-3 py-1.5 rounded-lg bg-steamAccent text-slate-900 font-bold shadow transition">7 Días (1 Sem)</button>
                    <button onclick="setChartRange(30)" id="btn-30d" class="px-3 py-1.5 rounded-lg text-gray-400 hover:text-white transition">30 Días (1 Mes)</button>
                </div>
            </div>
            <div class="relative h-[340px] w-full">
                <canvas id="portfolioChart"></canvas>
            </div>
        </div>

        <!-- TABLA DE POSICIONES Y OPORTUNIDADES ACTIVAS -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            <!-- OPORTUNIDADES PENDIENTES DE APROBACIÓN (SÍ / NO) -->
            <div class="bg-steamCard p-6 rounded-2xl border border-gray-800">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-bold text-white">⚡ Oportunidades Detectadas</h3>
                    <span class="text-xs text-gray-400">Decide con 1 clic: SÍ / NO</span>
                </div>
                <div id="pending-list" class="space-y-3">
                    <p class="text-gray-500 text-sm py-4 text-center">No hay oportunidades pendientes por confirmar en este momento.</p>
                </div>
            </div>

            <!-- POSICIONES ACTIVAS EN CARTERA -->
            <div class="bg-steamCard p-6 rounded-2xl border border-gray-800">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-bold text-white">📦 Activos en Seguimiento</h3>
                    <span class="text-xs text-gray-400">Monitoreo de precio y venta</span>
                </div>
                <div id="active-list" class="space-y-3">
                    <p class="text-gray-500 text-sm py-4 text-center">Aún no tienes activos en cartera.</p>
                </div>
            </div>

        </div>

    </div>

    <!-- MODAL MODIFICAR BALANCE -->
    <div id="modal-balance" class="fixed inset-0 bg-black/70 backdrop-blur-sm hidden flex items-center justify-center p-4 z-50">
        <div class="bg-steamCard border border-gray-700 p-6 rounded-2xl max-w-md w-full shadow-2xl space-y-4">
            <h3 class="text-xl font-bold text-white">✏️ Actualizar Mi Saldo de Cartera</h3>
            <p class="text-sm text-gray-400">Introduce el dinero real que tienes disponible en tu cartera de Steam (en Soles PEN) para que el bot dimensione las operaciones de forma exacta.</p>
            
            <div>
                <label class="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1">Tipo de Cartera</label>
                <select id="modal-mode" class="w-full bg-steamDark border border-gray-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-steamAccent text-sm">
                    <option value="REAL">Mi Cartera Real (Ej. S/ 150)</option>
                    <option value="SIMULATED">Simulador Virtual</option>
                </select>
            </div>

            <div>
                <label class="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1">Monto en Efectivo (S/)</label>
                <input type="number" step="0.5" id="modal-amount" placeholder="Ej. 150.00" class="w-full bg-steamDark border border-gray-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-steamAccent text-sm">
            </div>

            <div class="flex justify-end gap-3 pt-2">
                <button onclick="closeModal('modal-balance')" class="px-4 py-2 rounded-xl text-gray-400 hover:text-white text-sm font-semibold transition">Cancelar</button>
                <button onclick="submitNewBalance()" class="bg-steamAccent hover:bg-sky-400 text-slate-900 font-bold px-5 py-2 rounded-xl text-sm transition">Guardar Saldo</button>
            </div>
        </div>
    </div>

    <!-- MODAL VINCULACIÓN STEAM QR (24/7 NUBE Y MÓVIL) -->
    <div id="modal-steam-qr" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center hidden p-4">
        <div class="bg-steamCard border border-gray-700 w-full max-w-md rounded-2xl p-6 space-y-4 shadow-2xl relative">
            <div class="flex justify-between items-center border-b border-gray-800 pb-3">
                <h3 class="text-lg font-bold text-white flex items-center gap-2">
                    <span>📱</span> Vincular Steam Móvil (24/7)
                </h3>
                <button onclick="closeSteamQrModal()" class="text-gray-400 hover:text-white text-xl">✕</button>
            </div>
            <p class="text-xs text-gray-300">
                Escanea este código con la app de Steam en tu celular para activar la sesión permanente (OAuth Refresh Token). <b>Tu bot funcionará 24/7 aunque tu PC esté apagada.</b>
            </p>
            
            <div class="flex flex-col items-center justify-center p-4 bg-white rounded-xl my-2 min-h-[240px] shadow-inner">
                <div id="qr-loading" class="text-slate-700 font-semibold text-sm animate-pulse text-center">
                    ⏳ Conectando con servidores de Steam...
                </div>
                <img id="qr-image" src="" alt="Steam QR" class="hidden w-56 h-56 object-contain" />
            </div>

            <div id="qr-status-msg" class="text-xs text-center text-amber-300 bg-amber-950/40 border border-amber-800/40 p-2.5 rounded-lg">
                1. Abre la app de <b>Steam</b> en tu celular<br>
                2. Toca el menú <b>Steam Guard</b> > <b>"Escanear código QR"</b>
            </div>

            <div class="flex justify-between items-center pt-2 border-t border-gray-800">
                <button onclick="requestNewQrCode()" class="text-xs text-steamAccent hover:underline flex items-center gap-1">
                    🔄 Regenerar Código
                </button>
                <button onclick="closeSteamQrModal()" class="px-4 py-2 rounded-xl text-gray-400 hover:text-white text-sm font-semibold transition">
                    Cerrar
                </button>
            </div>
        </div>
    </div>

    <!-- SCRIPT DE CONTROL Y CHART.JS -->
    <script>
        let chartInstance = null;
        let currentDays = 7;

        function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
        function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

        async function fetchDashboardData() {
            try {
                const res = await fetch('/api/data');
                return await res.json();
            } catch (e) {
                console.error("Error al obtener datos:", e);
                return null;
            }
        }

        async function refreshData() {
            const data = await fetchDashboardData();
            if (!data) return;

            // Actualizar tarjetas principales
            document.getElementById('real-total').textContent = `S/ ${data.real.total_equity.toFixed(2)}`;
            document.getElementById('real-cash').textContent = `S/ ${data.real.cash_balance.toFixed(2)}`;
            document.getElementById('real-inv').textContent = `S/ ${data.real.inventory_value.toFixed(2)}`;

            document.getElementById('sim-total').textContent = `S/ ${data.simulated.total_equity.toFixed(2)}`;
            document.getElementById('sim-cash').textContent = `S/ ${data.simulated.cash_balance.toFixed(2)}`;
            document.getElementById('sim-inv').textContent = `S/ ${data.simulated.inventory_value.toFixed(2)}`;

            const profit = data.real.total_equity - 150.00;
            const profitEl = document.getElementById('total-profit');
            profitEl.textContent = `${profit >= 0 ? '+' : ''}S/ ${profit.toFixed(2)}`;
            profitEl.className = `text-3xl font-extrabold ${profit >= 0 ? 'text-steamGreen' : 'text-red-400'}`;

            document.getElementById('aggressive-badge').textContent = `${data.aggressive_count} / 3`;

            // Renderizar Oportunidades Pendientes
            const pendingContainer = document.getElementById('pending-list');
            if (data.pending_opportunities.length === 0) {
                pendingContainer.innerHTML = '<p class="text-gray-500 text-sm py-4 text-center">No hay oportunidades pendientes por confirmar.</p>';
            } else {
                pendingContainer.innerHTML = data.pending_opportunities.map(opp => `
                    <div class="p-4 bg-steamDark/80 rounded-xl border border-gray-800 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                        <div>
                            <div class="font-bold text-white text-sm">${opp.item_name} <span class="text-xs text-amber-400 ml-2">x${opp.quantity} unids</span></div>
                            <div class="text-xs text-gray-400 mt-1">
                                Precio: <b class="text-white">S/ ${opp.buy_price.toFixed(2)}</b> (Total: S/ ${opp.total_spent.toFixed(2)}) | Meta: <b class="text-steamGreen">S/ ${opp.target_sell_price.toFixed(2)}</b>
                            </div>
                        </div>
                        <div class="flex items-center gap-2 w-full sm:w-auto">
                            <button onclick="sendDecision(${opp.id}, true)" class="flex-1 sm:flex-none bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-3.5 py-2 rounded-lg font-bold transition">✅ SÍ, Invertí</button>
                            <button onclick="sendDecision(${opp.id}, false)" class="flex-1 sm:flex-none bg-slate-700 hover:bg-slate-600 text-gray-300 text-xs px-3.5 py-2 rounded-lg font-semibold transition">❌ NO</button>
                        </div>
                    </div>
                `).join('');
            }

            // Renderizar Activos en Seguimiento
            const activeContainer = document.getElementById('active-list');
            if (data.active_positions.length === 0) {
                activeContainer.innerHTML = '<p class="text-gray-500 text-sm py-4 text-center">Aún no tienes activos en cartera.</p>';
            } else {
                activeContainer.innerHTML = data.active_positions.map(pos => `
                    <div class="p-4 bg-steamDark/80 rounded-xl border border-gray-800 flex justify-between items-center">
                        <div>
                            <div class="font-bold text-white text-sm flex items-center gap-2">
                                ${pos.item_name}
                                <span class="text-[10px] px-2 py-0.5 rounded font-semibold ${pos.is_real ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'}">
                                    ${pos.is_real ? 'REAL' : 'SIMULADO'}
                                </span>
                            </div>
                            <div class="text-xs text-gray-400 mt-1">
                                Comprado a: S/ ${pos.buy_price.toFixed(2)} x${pos.quantity} | Objetivo: <b class="text-steamGreen">S/ ${pos.target_sell_price.toFixed(2)}</b>
                            </div>
                        </div>
                        <div class="text-right">
                            <span class="text-xs bg-slate-800 px-2.5 py-1 rounded text-gray-300 font-medium">HOLDING</span>
                        </div>
                    </div>
                `).join('');
            }

            renderChart(data.history);
        }

        function setChartRange(days) {
            currentDays = days;
            ['btn-3d', 'btn-7d', 'btn-30d'].forEach(id => {
                const el = document.getElementById(id);
                el.className = 'px-3 py-1.5 rounded-lg text-gray-400 hover:text-white transition';
            });
            const activeBtn = document.getElementById(`btn-${days}d`);
            if (activeBtn) activeBtn.className = 'px-3 py-1.5 rounded-lg bg-steamAccent text-slate-900 font-bold shadow transition';
            refreshData();
        }

        function renderChart(history) {
            const ctx = document.getElementById('portfolioChart').getContext('2d');
            
            // Filtrar por días seleccionados
            const now = new Date();
            const cutoff = new Date(now.getTime() - (currentDays * 24 * 60 * 60 * 1000));
            
            let filtered = history.filter(h => new Date(h.timestamp) >= cutoff);
            if (filtered.length < 2) filtered = history; // Fallback

            const labels = filtered.map(h => {
                const d = new Date(h.timestamp);
                return `${d.getDate()}/${d.getMonth()+1} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
            });
            const realData = filtered.filter(h => h.mode === 'REAL').map(h => h.total_equity);
            const simData = filtered.filter(h => h.mode === 'SIMULATED').map(h => h.total_equity);

            if (chartInstance) chartInstance.destroy();

            chartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels.slice(-realData.length),
                    datasets: [
                        {
                            label: 'Mi Cartera Real (S/)',
                            data: realData,
                            borderColor: '#00ff88',
                            backgroundColor: 'rgba(0, 255, 136, 0.08)',
                            borderWidth: 2.5,
                            fill: true,
                            tension: 0.3
                        },
                        {
                            label: 'Simulador S/ 500 (S/)',
                            data: simData,
                            borderColor: '#a855f7',
                            borderWidth: 2,
                            borderDash: [4, 4],
                            fill: false,
                            tension: 0.3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', font: { size: 11 } } },
                        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', callback: v => `S/ ${v}` } }
                    },
                    plugins: {
                        legend: { labels: { color: '#e5e7eb', font: { weight: 'bold' } } },
                        tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: S/ ${ctx.raw.toFixed(2)}` } }
                    }
                }
            });
        }

        async function sendDecision(oppId, userSaidYes) {
            await fetch('/api/decision', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ opp_id: oppId, decision: userSaidYes ? 'yes' : 'no' })
            });
            refreshData();
        }

        async function submitNewBalance() {
            const mode = document.getElementById('modal-mode').value;
            const amount = parseFloat(document.getElementById('modal-amount').value);
            if (isNaN(amount) || amount < 0) {
                alert('Por favor introduce un monto válido.');
                return;
            }
            await fetch('/api/update_balance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: mode, cash_balance: amount })
            });
            closeModal('modal-balance');
            refreshData();
        }

        // CONTROL DE SESIÓN STEAM QR 24/7
        let steamPollTimer = null;

        async function checkSteamStatus() {
            try {
                const res = await fetch('/api/steam/status');
                const data = await res.json();
                const container = document.getElementById('steam-status-container');
                if (data.authenticated) {
                    const bal = data.wallet_balance !== null ? `S/ ${data.wallet_balance.toFixed(2)}` : 'Sincronizando...';
                    container.innerHTML = `
                        <div class="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 rounded-xl text-xs">
                            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                            <span class="font-bold text-white">${data.account_name}</span>
                            <span class="text-emerald-300 font-semibold">(${bal})</span>
                            <button onclick="syncSteamWallet()" title="Sincronizar saldo de Steam" class="text-gray-400 hover:text-white ml-1">🔄</button>
                            <button onclick="logoutSteam()" title="Cerrar sesión" class="text-gray-400 hover:text-red-400 ml-1">🚪</button>
                        </div>
                    `;
                } else {
                    container.innerHTML = `
                        <button onclick="openSteamQrModal()" class="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white text-xs px-3.5 py-2 rounded-xl font-bold shadow-lg transition">
                            <span>📱</span> Vincular Steam Móvil (24/7)
                        </button>
                    `;
                }
            } catch (e) {
                console.error("Error al consultar estado de Steam:", e);
            }
        }

        async function openSteamQrModal() {
            openModal('modal-steam-qr');
            await requestNewQrCode();
        }

        function closeSteamQrModal() {
            closeModal('modal-steam-qr');
            if (steamPollTimer) {
                clearInterval(steamPollTimer);
                steamPollTimer = null;
            }
        }

        async function requestNewQrCode() {
            if (steamPollTimer) clearInterval(steamPollTimer);
            const qrImg = document.getElementById('qr-image');
            const qrLoading = document.getElementById('qr-loading');
            const statusMsg = document.getElementById('qr-status-msg');

            qrImg.classList.add('hidden');
            qrLoading.classList.remove('hidden');
            qrLoading.textContent = '⏳ Conectando con servidores de Steam...';
            statusMsg.innerHTML = '1. Abre la app de <b>Steam</b> en tu celular<br>2. Toca el menú <b>Steam Guard</b> > <b>"Escanear código QR"</b>';
            statusMsg.className = 'text-xs text-center text-amber-300 bg-amber-950/40 border border-amber-800/40 p-2.5 rounded-lg';

            try {
                const res = await fetch('/api/steam/qr');
                const data = await res.json();
                if (data.success && data.qr_image_base64) {
                    qrImg.src = data.qr_image_base64;
                    qrImg.classList.remove('hidden');
                    qrLoading.classList.add('hidden');

                    const intervalMs = (data.interval || 5) * 1000;
                    steamPollTimer = setInterval(pollSteamQr, intervalMs);
                } else {
                    qrLoading.textContent = '❌ ' + (data.error || 'No se pudo generar QR');
                }
            } catch (e) {
                qrLoading.textContent = '❌ Error de red al solicitar QR';
            }
        }

        async function pollSteamQr() {
            try {
                const res = await fetch('/api/steam/poll');
                const data = await res.json();
                const statusMsg = document.getElementById('qr-status-msg');

                if (data.status === 'approved') {
                    if (steamPollTimer) clearInterval(steamPollTimer);
                    statusMsg.innerHTML = `🎉 <b>¡Autenticado con éxito!</b> Bienvenido <b>${data.account_name}</b>. Guardando sesión permanente...`;
                    statusMsg.className = 'text-xs text-center text-emerald-300 bg-emerald-950/40 border border-emerald-800/40 p-2.5 rounded-lg';
                    setTimeout(() => {
                        closeSteamQrModal();
                        checkSteamStatus();
                        refreshData();
                    }, 1500);
                } else if (data.status === 'error') {
                    if (steamPollTimer) clearInterval(steamPollTimer);
                    statusMsg.innerHTML = `⚠️ Error: ${data.message}`;
                    statusMsg.className = 'text-xs text-center text-red-300 bg-red-950/40 border border-red-800/40 p-2.5 rounded-lg';
                }
            } catch (e) {
                console.error("Error al sondear estado de QR:", e);
            }
        }

        async function syncSteamWallet() {
            await fetch('/api/steam/sync', { method: 'POST' });
            checkSteamStatus();
            refreshData();
        }

        async function logoutSteam() {
            if (!confirm('¿Deseas desconectar tu cuenta de Steam del bot?')) return;
            await fetch('/api/steam/logout', { method: 'POST' });
            checkSteamStatus();
            refreshData();
        }

        // Inicializar
        checkSteamStatus();
        refreshData();
        setInterval(refreshData, 30000); // Refresco automático cada 30 seg
        setInterval(checkSteamStatus, 60000); // Refresco de sesión cada 60 seg
    </script>
</body>
</html>
"""

class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_DASHBOARD.encode("utf-8"))
            return

        elif parsed.path == "/api/data":
            conn = get_connection()
            cursor = conn.cursor()

            real_cash, real_inv, real_eq = get_current_capital(is_real=True)
            sim_cash, sim_inv, sim_eq = get_current_capital(is_real=False)
            agg_count = get_today_aggressive_count()

            # Posiciones pendientes de confirmación
            cursor.execute("SELECT * FROM portfolio WHERE status = 'PENDING_CONFIRMATION' ORDER BY id DESC")
            pending = [dict(r) for r in cursor.fetchall()]

            # Posiciones activas
            cursor.execute("SELECT * FROM portfolio WHERE status IN ('REAL_ACTIVE', 'SIMULATED') ORDER BY id DESC")
            active = [dict(r) for r in cursor.fetchall()]

            # Historial para gráficos
            cursor.execute("SELECT timestamp, mode, cash_balance, inventory_value, total_equity FROM capital_ledger ORDER BY timestamp ASC")
            history = [dict(r) for r in cursor.fetchall()]

            conn.close()

            payload = {
                "real": {"cash_balance": real_cash, "inventory_value": real_inv, "total_equity": real_eq},
                "simulated": {"cash_balance": sim_cash, "inventory_value": sim_inv, "total_equity": sim_eq},
                "aggressive_count": agg_count,
                "pending_opportunities": pending,
                "active_positions": active,
                "history": history
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        elif parsed.path == "/api/steam/status":
            status = steam_auth_mgr.get_status()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(status).encode("utf-8"))
            return

        elif parsed.path == "/api/steam/qr":
            qr_res = steam_auth_mgr.start_qr_session()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(qr_res).encode("utf-8"))
            return

        elif parsed.path == "/api/steam/poll":
            poll_res = steam_auth_mgr.poll_qr_status()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(poll_res).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        data = json.loads(body) if body else {}

        if parsed.path == "/api/decision":
            opp_id = int(data.get("opp_id"))
            user_said_yes = (data.get("decision") == "yes")
            result = process_user_decision(opp_id, user_said_yes)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "result": result}).encode("utf-8"))
            return

        elif parsed.path == "/api/update_balance":
            mode = data.get("mode", "REAL")
            new_cash = float(data.get("cash_balance", 150.0))
            is_real = (mode == "REAL")
            
            _, inv, _ = get_current_capital(is_real=is_real)
            new_eq = new_cash + inv
            now_str = datetime.datetime.now().isoformat()

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO capital_ledger (timestamp, mode, cash_balance, inventory_value, total_equity, notes)
            VALUES (?, ?, ?, ?, ?, 'Ajuste desde Web Dashboard')
            """, (now_str, mode, new_cash, inv, new_eq))
            conn.commit()
            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "new_cash": new_cash}).encode("utf-8"))
            return

        elif parsed.path == "/api/steam/sync":
            bal = steam_auth_mgr.fetch_wallet_balance()
            if bal is not None:
                update_real_wallet_balance(bal)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "balance": bal}).encode("utf-8"))
            return

        elif parsed.path == "/api/steam/logout":
            steam_auth_mgr.logout()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def run_web_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"🌐 Panel Web de SteamVault corriendo en: http://localhost:{PORT}")
        print(f"🌐 Para hacerlo público: expone el puerto {PORT} mediante Cloudflare Tunnel, Railway o Render.")
        httpd.serve_forever()

if __name__ == "__main__":
    run_web_server()
