CREATE TABLE decisions (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    decided TEXT NOT NULL,
    alternatives TEXT,
    reasoning TEXT,
    decided_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_decisions_tenant_decided_at ON decisions(tenant_id, decided_at DESC);
CREATE INDEX idx_decisions_tenant_id ON decisions(tenant_id);