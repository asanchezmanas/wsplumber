-- ============================================
-- EL FONTANERO DE WALL STREET
-- Schema de Base de Datos para Supabase
-- ============================================
-- 
-- Ejecutar este script en el SQL Editor de Supabase
-- para crear todas las tablas necesarias.
--
-- ============================================

-- Habilitar extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABLA: cycles (Ciclos principales y recovery)
-- ============================================
CREATE TABLE IF NOT EXISTS cycles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(50) UNIQUE NOT NULL,  -- "EURUSD_001"
    pair VARCHAR(10) NOT NULL,
    cycle_type VARCHAR(20) NOT NULL,  -- 'main', 'recovery'
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    parent_cycle_id UUID REFERENCES cycles(id),
    recovery_level INTEGER DEFAULT 0,
    
    -- Contabilidad
    pips_locked DECIMAL(10,2) DEFAULT 0,
    pips_recovered DECIMAL(10,2) DEFAULT 0,
    total_cost DECIMAL(10,2) DEFAULT 0,
    realized_profit DECIMAL(10,2) DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    activated_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    
    -- Metadata flexible (JSONB)
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT valid_cycle_type CHECK (cycle_type IN ('main', 'recovery')),
    CONSTRAINT valid_cycle_status CHECK (status IN ('active', 'hedged', 'in_recovery', 'closed', 'paused'))
);

-- Índices para cycles
CREATE INDEX IF NOT EXISTS idx_cycles_pair_status ON cycles(pair, status);
CREATE INDEX IF NOT EXISTS idx_cycles_created ON cycles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cycles_parent ON cycles(parent_cycle_id) WHERE parent_cycle_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cycles_external_id ON cycles(external_id);

-- ============================================
-- TABLA: operations (Todas las operaciones)
-- ============================================
CREATE TABLE IF NOT EXISTS operations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(50) UNIQUE NOT NULL,  -- "EURUSD_001_BUY"
    cycle_id UUID NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
    
    -- Identificación
    pair VARCHAR(10) NOT NULL,
    op_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    
    -- Precios
    entry_price DECIMAL(10,5) NOT NULL,
    tp_price DECIMAL(10,5) NOT NULL,
    actual_entry_price DECIMAL(10,5),
    actual_close_price DECIMAL(10,5),
    
    -- Tamaño
    lot_size DECIMAL(5,2) NOT NULL,
    pips_target DECIMAL(10,2) NOT NULL,
    
    -- Resultado
    profit_pips DECIMAL(10,2) DEFAULT 0,
    profit_eur DECIMAL(10,2) DEFAULT 0,
    
    -- Costos
    commission_open DECIMAL(10,2) DEFAULT 7.0,
    commission_close DECIMAL(10,2) DEFAULT 7.0,
    swap_total DECIMAL(10,2) DEFAULT 0,
    slippage_pips DECIMAL(5,2) DEFAULT 0,
    
    -- Broker
    broker_ticket VARCHAR(50),
    broker_response JSONB,
    
    -- Relaciones
    linked_operation_id VARCHAR(50),
    recovery_id VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    activated_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT valid_op_type CHECK (op_type IN (
        'main_buy', 'main_sell',
        'hedge_buy', 'hedge_sell', 
        'recovery_buy', 'recovery_sell'
    )),
    CONSTRAINT valid_op_status CHECK (status IN (
        'pending', 'active', 'tp_hit', 'neutralized', 'closed', 'cancelled'
    ))
);

-- Índices para operations
CREATE INDEX IF NOT EXISTS idx_operations_cycle ON operations(cycle_id);
CREATE INDEX IF NOT EXISTS idx_operations_status ON operations(status) WHERE status IN ('pending', 'active');
CREATE INDEX IF NOT EXISTS idx_operations_pair_type ON operations(pair, op_type);
CREATE INDEX IF NOT EXISTS idx_operations_broker_ticket ON operations(broker_ticket) WHERE broker_ticket IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_operations_created ON operations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_operations_external_id ON operations(external_id);

-- ============================================
-- TABLA: checkpoints (Estado del sistema)
-- ============================================
CREATE TABLE IF NOT EXISTS checkpoints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Estado completo en JSONB
    state JSONB NOT NULL,
    
    -- Metadata
    version VARCHAR(10) NOT NULL DEFAULT '2.0',
    config_hash VARCHAR(64),
    trigger_reason VARCHAR(50),
    
    -- Validación
    cycles_count INTEGER,
    operations_count INTEGER,
    checksum VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_created ON checkpoints(created_at DESC);

-- ============================================
-- TABLA: outbox (Patrón Outbox)
-- ============================================
CREATE TABLE IF NOT EXISTS outbox (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operation_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 5,
    idempotency_key VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    next_retry_at TIMESTAMPTZ,
    error_message TEXT,
    
    CONSTRAINT valid_outbox_status CHECK (status IN (
        'pending', 'processing', 'completed', 'failed', 'dead_letter'
    ))
);

CREATE INDEX IF NOT EXISTS idx_outbox_pending ON outbox(created_at) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_outbox_dead_letter ON outbox(created_at) WHERE status = 'dead_letter';

-- ============================================
-- TABLA: reconciliation_log
-- ============================================
CREATE TABLE IF NOT EXISTS reconciliation_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    local_operations INTEGER,
    broker_operations INTEGER,
    matched INTEGER,
    discrepancies JSONB,
    actions_taken JSONB,
    
    success BOOLEAN,
    duration_ms INTEGER,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_reconciliation_created ON reconciliation_log(created_at DESC);

-- ============================================
-- TABLA: metrics_daily
-- ============================================
CREATE TABLE IF NOT EXISTS metrics_daily (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    pair VARCHAR(10),
    
    -- Ciclos
    cycles_opened INTEGER DEFAULT 0,
    cycles_closed INTEGER DEFAULT 0,
    recovery_created INTEGER DEFAULT 0,
    
    -- Resultado
    main_tps_hit INTEGER DEFAULT 0,
    recovery_tps_hit INTEGER DEFAULT 0,
    pips_gross DECIMAL(10,2) DEFAULT 0,
    pips_net DECIMAL(10,2) DEFAULT 0,
    profit_eur DECIMAL(10,2) DEFAULT 0,
    
    -- Costos
    total_commissions DECIMAL(10,2) DEFAULT 0,
    total_swaps DECIMAL(10,2) DEFAULT 0,
    total_slippage DECIMAL(10,2) DEFAULT 0,
    
    -- Reserva
    to_reserve_fund DECIMAL(10,2) DEFAULT 0,
    
    -- Riesgo
    max_drawdown_pips DECIMAL(10,2) DEFAULT 0,
    max_concurrent_operations INTEGER DEFAULT 0,
    max_exposure_percent DECIMAL(5,2) DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(date, pair)
);

CREATE INDEX IF NOT EXISTS idx_metrics_date ON metrics_daily(date DESC);

-- ============================================
-- TABLA: reserve_fund
-- ============================================
CREATE TABLE IF NOT EXISTS reserve_fund (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    transaction_type VARCHAR(20) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    balance_after DECIMAL(10,2) NOT NULL,
    
    source_operation_id UUID REFERENCES operations(id),
    reason TEXT,
    
    CONSTRAINT valid_transaction_type CHECK (transaction_type IN (
        'deposit', 'withdrawal', 'gap_coverage', 'drawdown_coverage', 'adjustment'
    ))
);

CREATE INDEX IF NOT EXISTS idx_reserve_fund_created ON reserve_fund(created_at DESC);

-- ============================================
-- TABLA: alerts
-- ============================================
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    severity VARCHAR(20) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    
    pair VARCHAR(10),
    cycle_id UUID REFERENCES cycles(id),
    operation_id UUID REFERENCES operations(id),
    metadata JSONB,
    
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_alerts_unacknowledged ON alerts(created_at DESC) WHERE acknowledged = FALSE;
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity, created_at DESC);

-- ============================================
-- TABLA: error_log
-- ============================================
CREATE TABLE IF NOT EXISTS error_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    severity VARCHAR(20) NOT NULL,
    component VARCHAR(50),
    error_type VARCHAR(100),
    error_message TEXT,
    stack_trace TEXT,
    
    correlation_id VARCHAR(50),
    operation_id VARCHAR(50),
    cycle_id UUID REFERENCES cycles(id),
    
    metadata JSONB,
    
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_error_log_unresolved ON error_log(created_at DESC) WHERE resolved = FALSE;
CREATE INDEX IF NOT EXISTS idx_error_log_severity ON error_log(severity, created_at DESC);

-- ============================================
-- TABLA: connection_status
-- ============================================
CREATE TABLE IF NOT EXISTS connection_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    component VARCHAR(50) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL,
    last_connected TIMESTAMPTZ,
    last_disconnected TIMESTAMPTZ,
    reconnect_attempts INTEGER DEFAULT 0,
    last_error TEXT,
    latency_ms INTEGER,
    metadata JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- TABLA: circuit_breaker_status
-- ============================================
CREATE TABLE IF NOT EXISTS circuit_breaker_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE,
    state VARCHAR(20) NOT NULL,
    failures INTEGER DEFAULT 0,
    successes INTEGER DEFAULT 0,
    total_calls INTEGER DEFAULT 0,
    total_blocked INTEGER DEFAULT 0,
    last_failure_at TIMESTAMPTZ,
    last_state_change TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- TABLA: system_events
-- ============================================
CREATE TABLE IF NOT EXISTS system_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    event_type VARCHAR(50) NOT NULL,
    description TEXT,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_system_events_type ON system_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_events_recent ON system_events(created_at DESC);

-- ============================================
-- TABLA: config_history
-- ============================================
CREATE TABLE IF NOT EXISTS config_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    config_hash VARCHAR(64) NOT NULL,
    config JSONB NOT NULL,
    
    changed_by VARCHAR(100),
    change_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_config_history_created ON config_history(created_at DESC);

-- ============================================
-- VISTAS
-- ============================================

-- Vista: Estado actual del sistema
CREATE OR REPLACE VIEW v_system_status AS
SELECT 
    (SELECT COUNT(*) FROM cycles WHERE status = 'active') as active_cycles,
    (SELECT COUNT(*) FROM cycles WHERE status = 'in_recovery') as cycles_in_recovery,
    (SELECT COUNT(*) FROM operations WHERE status = 'active') as active_operations,
    (SELECT COUNT(*) FROM operations WHERE status = 'pending') as pending_operations,
    (SELECT COALESCE(SUM(pips_locked), 0) FROM cycles WHERE status != 'closed') as total_pips_locked,
    (SELECT balance_after FROM reserve_fund ORDER BY created_at DESC LIMIT 1) as reserve_fund_balance,
    (SELECT created_at FROM checkpoints ORDER BY created_at DESC LIMIT 1) as last_checkpoint;

-- Vista: Resumen por par
CREATE OR REPLACE VIEW v_pair_summary AS
SELECT 
    pair,
    COUNT(*) FILTER (WHERE status = 'active') as active_cycles,
    COUNT(*) FILTER (WHERE status = 'in_recovery') as in_recovery,
    COALESCE(SUM(pips_locked) FILTER (WHERE status != 'closed'), 0) as pips_locked,
    COUNT(*) FILTER (WHERE status = 'closed' AND closed_at > NOW() - INTERVAL '24 hours') as closed_today
FROM cycles
GROUP BY pair;

-- Vista: Operaciones activas con detalle
CREATE OR REPLACE VIEW v_active_operations AS
SELECT 
    o.external_id,
    o.pair,
    o.op_type,
    o.status,
    o.entry_price,
    o.tp_price,
    o.lot_size,
    o.created_at,
    o.activated_at,
    c.external_id as cycle_id,
    c.cycle_type,
    c.recovery_level
FROM operations o
JOIN cycles c ON o.cycle_id = c.id
WHERE o.status IN ('pending', 'active')
ORDER BY o.created_at DESC;

-- Vista: Errores sin resolver
CREATE OR REPLACE VIEW v_unresolved_errors AS
SELECT 
    id,
    created_at,
    severity,
    component,
    error_type,
    error_message,
    correlation_id,
    metadata
FROM error_log
WHERE resolved = FALSE
ORDER BY 
    CASE severity 
        WHEN 'critical' THEN 1 
        WHEN 'error' THEN 2 
        WHEN 'warning' THEN 3 
        ELSE 4 
    END,
    created_at DESC;

-- Vista: Dead letter queue
CREATE OR REPLACE VIEW v_dead_letter_queue AS
SELECT 
    id,
    operation_type,
    payload,
    attempts,
    created_at,
    error_message
FROM outbox
WHERE status = 'dead_letter'
ORDER BY created_at DESC;

-- Vista: Dashboard de salud
CREATE OR REPLACE VIEW v_system_health_dashboard AS
SELECT 
    (SELECT COUNT(*) FROM cycles WHERE status = 'active') as active_cycles,
    (SELECT COUNT(*) FROM operations WHERE status IN ('pending', 'active')) as active_operations,
    (SELECT COUNT(*) FROM error_log WHERE resolved = FALSE AND severity = 'critical') as critical_errors,
    (SELECT COUNT(*) FROM error_log WHERE resolved = FALSE AND severity = 'error') as errors,
    (SELECT COUNT(*) FROM outbox WHERE status = 'dead_letter') as dead_letters,
    (SELECT COUNT(*) FROM circuit_breaker_status WHERE state = 'open') as open_circuit_breakers,
    (SELECT COUNT(*) FROM connection_status WHERE status != 'connected') as disconnected_components,
    (SELECT balance_after FROM reserve_fund ORDER BY created_at DESC LIMIT 1) as reserve_fund_balance,
    (SELECT created_at FROM checkpoints ORDER BY created_at DESC LIMIT 1) as last_checkpoint;

-- ============================================
-- FUNCIONES
-- ============================================

-- Función: Obtener siguiente ID de ciclo
CREATE OR REPLACE FUNCTION get_next_cycle_id(p_pair VARCHAR)
RETURNS VARCHAR AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) + 1 INTO v_count
    FROM cycles
    WHERE pair = p_pair;
    
    RETURN p_pair || '_' || LPAD(v_count::TEXT, 3, '0');
END;
$$ LANGUAGE plpgsql;

-- Función: Calcular balance de un ciclo
CREATE OR REPLACE FUNCTION calculate_cycle_balance(p_cycle_id UUID)
RETURNS DECIMAL AS $$
DECLARE
    v_balance DECIMAL;
BEGIN
    SELECT COALESCE(SUM(profit_pips - commission_open - commission_close - swap_total), 0)
    INTO v_balance
    FROM operations
    WHERE cycle_id = p_cycle_id;
    
    RETURN v_balance;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- TRIGGERS
-- ============================================

-- Trigger: Alerta si drawdown alto
CREATE OR REPLACE FUNCTION check_drawdown_alert()
RETURNS TRIGGER AS $$
DECLARE
    v_total_locked DECIMAL;
BEGIN
    SELECT COALESCE(SUM(pips_locked), 0) INTO v_total_locked
    FROM cycles WHERE status != 'closed';
    
    IF v_total_locked > 300 AND v_total_locked <= 500 THEN
        INSERT INTO alerts (severity, alert_type, message, metadata)
        VALUES (
            'warning',
            'high_drawdown',
            'Pips locked alto: ' || v_total_locked,
            jsonb_build_object('pips_locked', v_total_locked)
        );
    ELSIF v_total_locked > 500 THEN
        INSERT INTO alerts (severity, alert_type, message, metadata)
        VALUES (
            'critical',
            'critical_drawdown',
            'CRÍTICO: Pips locked muy alto: ' || v_total_locked,
            jsonb_build_object('pips_locked', v_total_locked)
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_drawdown
AFTER INSERT OR UPDATE ON cycles
FOR EACH ROW EXECUTE FUNCTION check_drawdown_alert();

-- ============================================
-- DATOS INICIALES
-- ============================================

-- Insertar estado inicial de conexiones
INSERT INTO connection_status (component, status) VALUES 
    ('broker_mt5', 'disconnected'),
    ('broker_darwinex', 'disconnected'),
    ('supabase', 'connected')
ON CONFLICT (component) DO NOTHING;

-- Insertar fondo de reserva inicial
INSERT INTO reserve_fund (transaction_type, amount, balance_after, reason)
SELECT 'adjustment', 0, 0, 'Initial balance'
WHERE NOT EXISTS (SELECT 1 FROM reserve_fund);

-- ============================================
-- PERMISOS (ajustar según necesidades)
-- ============================================

-- Habilitar RLS (Row Level Security) si se necesita multi-usuario
-- ALTER TABLE cycles ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE operations ENABLE ROW LEVEL SECURITY;

-- ============================================
-- FIN DEL SCRIPT
-- ============================================
