CREATE TABLE IF NOT EXISTS investor_relationships (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    investor_name TEXT NOT NULL,
    firm TEXT NOT NULL,
    last_contact_at TIMESTAMP WITH TIME ZONE,
    warm_up_days INTEGER DEFAULT 30,
    raise_priority INTEGER DEFAULT 5,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS investor_interactions (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    investor_id INTEGER REFERENCES investor_relationships(id) ON DELETE CASCADE,
    interaction_type TEXT NOT NULL,
    summary TEXT,
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_investor_relationships_tenant ON investor_relationships(tenant_id);
CREATE INDEX IF NOT EXISTS idx_investor_relationships_last_contact ON investor_relationships(tenant_id, last_contact_at DESC);
CREATE INDEX IF NOT EXISTS idx_investor_interactions_tenant ON investor_interactions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_investor_interactions_investor ON investor_interactions(investor_id);