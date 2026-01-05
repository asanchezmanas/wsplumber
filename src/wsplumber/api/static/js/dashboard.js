/**
 * dashboard.js - WebSocket Client para El Fontanero de Wall Street
 * ===============================================================
 * Conexión en tiempo real con el backend para actualizar:
 * - Radial Gauges (Equity, Pips, Exposure, Efficiency)
 * - News Ticker (últimas señales)
 * - FIFO Ledger Table (ciclos activos)
 */

class DashboardClient {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;

        // DOM References (se cachean una vez)
        this.elements = {
            gauges: {
                balance: document.getElementById('gauge-balance'),
                pips: document.getElementById('gauge-pips'),
                volatility: document.getElementById('gauge-volatility'),
                efficiency: document.getElementById('gauge-efficiency'),
            },
            ticker: document.getElementById('news-ticker'),
            fifoTable: document.getElementById('fifo-table-body'),
            connectionStatus: document.getElementById('connection-status'),
        };
    }

    /**
     * Inicializa la conexión WebSocket
     */
    connect() {
        const wsUrl = `ws://${window.location.host}/ws/dashboard`;
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
        this.updateConnectionStatus(true);
    }

    handleMessage(event) {
        try {
            const message = JSON.parse(event.data);
            console.log('[WS] Received:', message.type);

            switch (message.type) {
                case 'initial_state':
                    this.updateAllComponents(message.data);
                    break;
                case 'state_update':
                    this.updateAllComponents(message.data);
                    break;
                case 'ticker_event':
                    this.addTickerEvent(message.data);
                    break;
                case 'cycle_update':
                    this.updateFifoRow(message.data);
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
        this.updateConnectionStatus(false);
        this.attemptReconnect();
    }

    handleError(error) {
        console.error('[WS] Error:', error);
        this.updateConnectionStatus(false);
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`[WS] Reconnecting (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            setTimeout(() => this.connect(), this.reconnectDelay);
        } else {
            console.error('[WS] Max reconnect attempts reached. Giving up.');
        }
    }

    /**
     * Actualiza todos los componentes con los datos recibidos
     */
    updateAllComponents(data) {
        if (data.equity !== undefined) {
            this.updateGauge('balance', data.equity, 135000, '+' + data.equity_change + '%');
        }
        if (data.daily_pips !== undefined) {
            this.updateGauge('pips', data.daily_pips, 10, data.daily_pips > 10 ? '+' + ((data.daily_pips / 10 - 1) * 100).toFixed(0) + '%' : '');
        }
        if (data.exposure !== undefined) {
            this.updateGauge('volatility', data.exposure * 3, 100, data.exposure < 10 ? 'Normal' : 'Elevated');
        }
        if (data.active_cycles !== undefined) {
            this.updateGauge('efficiency', 92, 100, 'Optimal');
        }
    }

    /**
     * Actualiza un gauge radial SVG
     */
    updateGauge(gaugeId, value, max, label) {
        const gauge = this.elements.gauges[gaugeId];
        if (!gauge) return;

        const percentage = Math.min((value / max) * 100, 100);
        const circle = gauge.querySelector('circle:last-of-type');
        const valueEl = gauge.querySelector('.gauge-value');
        const labelEl = gauge.querySelector('.gauge-label');

        if (circle) {
            circle.setAttribute('stroke-dasharray', `${percentage}, 100`);
        }
        if (valueEl) {
            valueEl.textContent = typeof value === 'number' ? value.toLocaleString() : value;
        }
        if (labelEl && label) {
            labelEl.textContent = label;
        }
    }

    /**
     * Añade un evento al ticker
     */
    addTickerEvent(eventData) {
        const ticker = this.elements.ticker;
        if (!ticker) return;

        const span = document.createElement('span');
        span.className = 'text-[9px] font-black text-primary-light uppercase tracking-tighter flex items-center gap-2';
        span.innerHTML = `
            <span class="w-1 h-1 rounded-full bg-primary animate-pulse"></span>
            ${eventData.pair}: ${eventData.message}
        `;

        ticker.appendChild(span);

        // Limitar a 10 eventos
        while (ticker.children.length > 10) {
            ticker.removeChild(ticker.firstChild);
        }
    }

    /**
     * Actualiza una fila del FIFO Ledger
     */
    updateFifoRow(cycleData) {
        const tbody = this.elements.fifoTable;
        if (!tbody) return;

        let row = tbody.querySelector(`[data-cycle-id="${cycleData.id}"]`);

        if (!row) {
            row = document.createElement('tr');
            row.setAttribute('data-cycle-id', cycleData.id);
            row.className = 'hover:bg-white/[0.02]';
            tbody.appendChild(row);
        }

        const statusClass = cycleData.status === 'HEALTHY' ? 'text-success' : 'text-orange-500';
        const plClass = cycleData.pnl >= 0 ? 'text-success' : 'text-danger';

        row.innerHTML = `
            <td class="px-6 py-4 flex items-center gap-2">
                <span class="w-4 h-4 rounded bg-primary/20 text-primary-light flex items-center justify-center text-[8px]">${cycleData.pair.substring(0, 2)}</span>
                ${cycleData.pair}
            </td>
            <td class="px-6 py-4 ${statusClass}">${cycleData.status}</td>
            <td class="px-6 py-4 text-text-muted">${cycleData.entry} / Lv${cycleData.level}</td>
            <td class="px-6 py-4 ${plClass}">${cycleData.pnl > 0 ? '+' : ''}${cycleData.pnl.toFixed(1)} pips</td>
            <td class="px-6 py-4 text-right">
                <button class="text-text-muted hover:text-white">
                    <span class="material-symbols-outlined text-lg">open_in_new</span>
                </button>
            </td>
        `;
    }

    /**
     * Actualiza el indicador de estado de conexión
     */
    updateConnectionStatus(connected) {
        const statusEl = this.elements.connectionStatus;
        if (!statusEl) return;

        if (connected) {
            statusEl.classList.remove('bg-danger');
            statusEl.classList.add('bg-success', 'animate-pulse');
        } else {
            statusEl.classList.remove('bg-success', 'animate-pulse');
            statusEl.classList.add('bg-danger');
        }
    }

    /**
     * Envía un mensaje al servidor
     */
    send(type, data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ type, data }));
        } else {
            console.warn('[WS] Cannot send - socket not open');
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardClient = new DashboardClient();
    window.dashboardClient.connect();
});
