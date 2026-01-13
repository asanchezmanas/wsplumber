/**
 * dashboard_v3.js - WebSocket Client para WSPlumber Dashboard V3
 * ==============================================================
 * Cliente optimizado para el nuevo dashboard premium con:
 * - Gauges radiales SVG
 * - Tablas de operaciones en tiempo real
 * - Métricas de recovery/debt
 * - News ticker animado
 */

class DashboardV3Client {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 3000;
        this.isConnected = false;

        // Cache DOM references
        this.elements = {
            // Header
            headerAccount: document.getElementById('header-account'),

            // Card 1: Balance
            balanceValue: document.getElementById('balance-value'),
            balanceChange: document.getElementById('balance-change'),
            balanceGauge: document.getElementById('balance-gauge'),
            balancePercent: document.getElementById('balance-percent'),
            balanceCurrent: document.getElementById('balance-current'),

            // Card 2: Pips
            pipsValue: document.getElementById('pips-value'),
            pipsChange: document.getElementById('pips-change'),
            pipsGauge: document.getElementById('pips-gauge'),
            pipsPercent: document.getElementById('pips-percent'),
            pipsCurrent: document.getElementById('pips-current'),

            // Card 3: Exposure
            exposureValue: document.getElementById('exposure-value'),
            exposurePercentBadge: document.getElementById('exposure-percent-badge'),
            exposureGauge: document.getElementById('exposure-gauge'),
            exposurePercent: document.getElementById('exposure-percent'),
            exposureUsed: document.getElementById('exposure-used'),

            // Card 4: Recovery
            recoveryValue: document.getElementById('recovery-value'),
            recoveryCycles: document.getElementById('recovery-cycles'),
            recoveryGauge: document.getElementById('recovery-gauge'),
            recoveryPercent: document.getElementById('recovery-percent'),
            recoveryDone: document.getElementById('recovery-done'),
            recoveryPending: document.getElementById('recovery-pending'),

            // Sidebar stats
            tpsToday: document.getElementById('tps-today'),
            cyclesOpen: document.getElementById('cycles-open'),
            cyclesClosed: document.getElementById('cycles-closed'),
            recoveryActive: document.getElementById('recovery-active'),
            dailyPnl: document.getElementById('daily-pnl'),
            winRate: document.getElementById('win-rate'),
            opsToday: document.getElementById('ops-today'),
            currentBalance: document.getElementById('current-balance'),
            monthlyPips: document.getElementById('monthly-pips'),
            totalExposure: document.getElementById('total-exposure'),

            // Tables
            operationsTableBody: document.querySelector('#operations-table tbody'),
            eventsTableBody: document.querySelector('#events-table tbody'),
            closedOpsTableBody: document.querySelector('#closed-ops-table tbody'),
        };
    }

    /**
     * Initialize WebSocket connection
     */
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`;
        console.log(`[WS] Connecting to ${wsUrl}...`);

        this.socket = new WebSocket(wsUrl);
        this.socket.onopen = () => this.handleOpen();
        this.socket.onmessage = (event) => this.handleMessage(event);
        this.socket.onclose = (event) => this.handleClose(event);
        this.socket.onerror = (error) => this.handleError(error);
    }

    handleOpen() {
        console.log('[WS] Connected successfully');
        this.reconnectAttempts = 0;
        this.isConnected = true;
        this.updateConnectionIndicator(true);
    }

    handleMessage(event) {
        try {
            const message = JSON.parse(event.data);
            console.log('[WS] Received:', message.type);

            switch (message.type) {
                case 'initial_state':
                case 'state_update':
                    this.updateDashboard(message.data);
                    break;
                case 'ticker_event':
                    this.addTickerEvent(message.data);
                    break;
                case 'cycle_update':
                    this.updateCycleRow(message.data);
                    break;
                case 'pong':
                    console.log('[WS] Pong received');
                    break;
                default:
                    console.warn('[WS] Unknown message type:', message.type);
            }
        } catch (e) {
            console.error('[WS] Error parsing message:', e);
        }
    }

    handleClose(event) {
        console.log(`[WS] Connection closed (code: ${event.code})`);
        this.isConnected = false;
        this.updateConnectionIndicator(false);
        this.attemptReconnect();
    }

    handleError(error) {
        console.error('[WS] Error:', error);
        this.isConnected = false;
        this.updateConnectionIndicator(false);
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`[WS] Reconnecting (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            setTimeout(() => this.connect(), this.reconnectDelay);
        } else {
            console.error('[WS] Max reconnect attempts reached.');
        }
    }

    /**
     * Update all dashboard components with received data
     */
    updateDashboard(data) {
        // Card 1: Balance
        if (data.balance !== undefined) {
            this.updateBalance(data);
        }

        // Card 2: Pips
        if (data.daily_pips !== undefined) {
            this.updatePips(data);
        }

        // Card 3: Exposure
        if (data.exposure_pct !== undefined || data.total_lots !== undefined) {
            this.updateExposure(data);
        }

        // Card 4: Recovery
        if (data.pips_remaining !== undefined) {
            this.updateRecovery(data);
        }

        // Sidebar stats
        this.updateSidebarStats(data);

        // Operations table
        if (data.operations) {
            this.updateOperationsTable(data.operations);
        }
    }

    updateBalance(data) {
        const el = this.elements;
        if (el.balanceValue) {
            el.balanceValue.textContent = `€${data.balance.toLocaleString('es-ES', { minimumFractionDigits: 2 })}`;
        }
        if (el.balanceChange) {
            const change = data.equity - data.balance;
            const sign = change >= 0 ? '+' : '';
            el.balanceChange.textContent = `${sign}€${change.toFixed(2)}`;
            el.balanceChange.parentElement.className = change >= 0
                ? 'bg-green-50 text-green-600 text-[11px] px-2 py-1 rounded font-medium flex items-center gap-1'
                : 'bg-red-50 text-red-600 text-[11px] px-2 py-1 rounded font-medium flex items-center gap-1';
        }
        if (el.balanceCurrent) {
            el.balanceCurrent.textContent = `€${Math.floor(data.balance).toLocaleString()}`;
        }
        if (el.currentBalance) {
            el.currentBalance.textContent = `€${data.balance.toLocaleString('es-ES', { minimumFractionDigits: 2 })}`;
        }
    }

    updatePips(data) {
        const el = this.elements;
        if (el.pipsValue) {
            const sign = data.daily_pips >= 0 ? '+' : '';
            el.pipsValue.textContent = `${sign}${Math.round(data.daily_pips)}`;
            el.pipsValue.className = data.daily_pips >= 0
                ? 'text-2xl font-bold text-green-600 mt-1'
                : 'text-2xl font-bold text-red-600 mt-1';
        }
        if (el.pipsCurrent) {
            el.pipsCurrent.textContent = Math.round(data.daily_pips);
        }
        if (el.monthlyPips) {
            el.monthlyPips.textContent = `+${Math.round(data.daily_pips)} pips`;
        }
    }

    updateExposure(data) {
        const el = this.elements;
        if (el.exposureValue) {
            el.exposureValue.textContent = `${data.total_lots.toFixed(2)} lotes`;
        }
        if (el.exposurePercentBadge) {
            el.exposurePercentBadge.textContent = `${Math.round(data.exposure_pct)}%`;
        }
        if (el.exposurePercent) {
            el.exposurePercent.textContent = `${Math.round(data.exposure_pct)}%`;
        }
        if (el.exposureUsed) {
            el.exposureUsed.textContent = `€${Math.round(data.margin).toLocaleString()}`;
        }
        if (el.totalExposure) {
            el.totalExposure.textContent = `${data.total_lots.toFixed(2)} lotes`;
        }
    }

    updateRecovery(data) {
        const el = this.elements;
        if (el.recoveryValue) {
            const remaining = Math.round(data.pips_remaining);
            el.recoveryValue.textContent = remaining > 0 ? `-${remaining} pips` : '0 pips';
            el.recoveryValue.className = remaining > 0
                ? 'text-2xl font-bold text-red-600 mt-1'
                : 'text-2xl font-bold text-green-600 mt-1';
        }
        if (el.recoveryCycles) {
            el.recoveryCycles.textContent = `${data.cycles_in_recovery} ciclos`;
        }
        if (el.recoveryDone) {
            el.recoveryDone.textContent = `${Math.round(data.pips_recovered)} pips`;
        }
        if (el.recoveryPending) {
            const total = data.pips_remaining + data.pips_recovered;
            el.recoveryPending.textContent = `${Math.round(total)} pips`;
        }
        if (el.recoveryActive) {
            el.recoveryActive.textContent = data.cycles_in_recovery;
        }

        // Update gauge percentage
        if (el.recoveryPercent && data.pips_remaining + data.pips_recovered > 0) {
            const pct = Math.round((data.pips_recovered / (data.pips_remaining + data.pips_recovered)) * 100);
            el.recoveryPercent.textContent = `${pct}%`;
        }
    }

    updateSidebarStats(data) {
        const el = this.elements;
        if (el.cyclesOpen) el.cyclesOpen.textContent = data.active_cycles || 0;
        if (el.winRate) el.winRate.textContent = `${data.win_rate || 0}%`;
        if (el.dailyPnl) {
            const pnl = data.equity - data.balance;
            el.dailyPnl.textContent = pnl >= 0 ? `+€${pnl.toFixed(2)}` : `-€${Math.abs(pnl).toFixed(2)}`;
        }
    }

    updateOperationsTable(operations) {
        const tbody = this.elements.operationsTableBody;
        if (!tbody) return;

        // Clear existing rows (keep header)
        tbody.innerHTML = '';

        operations.forEach(op => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-slate-50';

            const typeIcon = op.type === 'Buy' ? '▲' : '▼';
            const typeColor = op.type === 'Buy' ? 'green' : 'red';
            const statusClass = this.getStatusClass(op.status);
            const pnlClass = op.pnl_pips >= 0 ? 'text-green-600' : 'text-red-600';
            const pnlSign = op.pnl_pips >= 0 ? '+' : '';
            const opType = op.is_recovery ? 'Recovery' : (op.type === 'Buy' ? 'Main Buy' : 'Hedge Sell');
            const opTypeColor = op.is_recovery ? 'text-orange-600' : (op.type === 'Buy' ? 'text-blue-600' : 'text-purple-600');

            row.innerHTML = `
                <td class="px-4 py-3"><span class="w-4 h-4 rounded-full bg-${typeColor}-100 text-${typeColor}-600 flex items-center justify-center text-[10px] font-bold">${typeIcon}</span></td>
                <td class="px-4 py-3 text-slate-900 font-medium">${op.pair}</td>
                <td class="px-4 py-3 ${opTypeColor}">${opType}</td>
                <td class="px-4 py-3"><span class="${statusClass}">${op.status}</span></td>
                <td class="px-4 py-3 ${pnlClass} font-medium">${pnlSign}${op.pnl_pips.toFixed(1)} pips</td>
                <td class="px-4 py-3 text-slate-500 text-right">${op.id}</td>
            `;
            tbody.appendChild(row);
        });
    }

    getStatusClass(status) {
        const classes = {
            'ACTIVE': 'px-2 py-0.5 bg-green-100 text-green-700 rounded text-[10px] font-medium',
            'PENDING': 'px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-[10px] font-medium',
            'IN_RECOVERY': 'px-2 py-0.5 bg-orange-100 text-orange-700 rounded text-[10px] font-medium',
            'CLOSED': 'px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-[10px] font-medium',
            'TP_HIT': 'px-2 py-0.5 bg-green-100 text-green-700 rounded text-[10px] font-medium',
        };
        return classes[status] || classes['PENDING'];
    }

    addTickerEvent(eventData) {
        const ticker = document.getElementById('news-ticker');
        if (!ticker) return;

        const container = ticker.querySelector('div');
        if (!container) return;

        const span = document.createElement('span');
        span.className = 'flex items-center gap-2';
        span.innerHTML = `
            <span class="w-1.5 h-1.5 bg-green-500 rounded-full"></span>
            ${eventData.pair}: ${eventData.message}
        `;
        container.appendChild(span);

        // Keep max 8 events
        while (container.children.length > 8) {
            container.removeChild(container.firstChild);
        }
    }

    updateConnectionIndicator(connected) {
        // Update header connection status
        const statusSpan = document.querySelector('header .text-green-600, header .text-red-600');
        if (statusSpan) {
            statusSpan.textContent = connected ? 'Conectado' : 'Desconectado';
            statusSpan.className = connected
                ? 'text-green-600 font-medium'
                : 'text-red-600 font-medium';
        }
    }

    /**
     * Send message to server
     */
    send(type, data = {}) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ type, data }));
        }
    }

    /**
     * Request fresh state from server
     */
    requestState() {
        this.send('request_state');
    }

    /**
     * Send ping to keep connection alive
     */
    ping() {
        this.send('ping');
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardClient = new DashboardV3Client();
    window.dashboardClient.connect();

    // Ping every 30 seconds to keep connection alive
    setInterval(() => {
        if (window.dashboardClient.isConnected) {
            window.dashboardClient.ping();
        }
    }, 30000);
});
