#!/bin/bash
set -e

echo "🚀 Starting IterateSwarm → Saarathi rename..."

# Create pre-rename tag
echo "📌 Creating pre-rename tag v1.2.0-pre-rename..."
git tag -a v1.2.0-pre-rename -m "Final state before IterateSwarm → Saarathi rename" 2>/dev/null || echo "Tag already exists, skipping..."

# Update docker-compose.yml
echo "🔄 Updating docker-compose.yml..."
sed -i 's/iterateswarm-/saarathi-/g' docker-compose.yml
sed -i 's/iterateswarm_default/saarathi_default/g' docker-compose.yml

# Update Go module paths
echo "🔄 Updating Go module paths..."
OLD="iterateswarm-core"
NEW="saarathi-core"
find apps/core -name "*.go" -exec sed -i "s|$OLD|$NEW|g" {} +

# Update go.mod
if [ -f "apps/core/go.mod" ]; then
    sed -i "s|module $OLD|module $NEW|g" apps/core/go.mod
fi

# Update Python projects
echo "🔄 Updating Python projects..."
find apps/ai -name "*.py" -exec sed -i 's/iterateswarm/saarathi/g' {} +
find apps/ai -name "*.toml" -exec sed -i 's/iterateswarm/saarathi/g' {} +

# Update environment variables
echo "🔄 Updating environment variables..."
sed -i 's/ITERATESWARM_/SAARATHI_/g' .env.example
find . -name "*.go" -exec sed -i 's/ITERATESWARM_/SAARATHI_/g' {} +

# Update Makefile
echo "🔄 Updating Makefile..."
sed -i 's/iterateswarm/saarathi/g' Makefile

# Update README
echo "🔄 Updating README references..."
sed -i 's/IterateSwarm/Saarathi/g' README.md
sed -i 's/iterate_swarm/saarathi/g' README.md

# Update package.json files if they exist
find . -name "package.json" -exec sed -i 's/iterateswarm/saarathi/g' {} +

# Commit changes
echo "📝 Committing changes..."
git add -A
git commit -m "chore: rename IterateSwarm → Saarathi

Complete rename across all services:
- Go module: iterateswarm-core → saarathi-core
- Docker containers: iterateswarm-* → saarathi-*
- Environment variables: ITERATESWARM_* → SAARATHI_*
- Python packages: iterateswarm → saarathi
- Documentation updates

Saarathi (सारथी) — The trusted intelligence that speaks at exactly the right moment."

# Create v2.0.0 tag
echo "🏷️  Creating v2.0.0 tag..."
git tag -a v2.0.0 -m "Saarathi — AI Co-Founder Agent

Week 3/3 Complete:
✅ HTMX Dashboard with SSE live updates
✅ Founder reflection tracking
✅ Commitment accountability loop
✅ Materialized view for dashboard analytics
✅ Energy trend sparklines
✅ Trigger history with founder feedback

The pivot from automation platform to accountability partner is complete."

echo ""
echo "✅ Rename complete!"
echo ""
echo "Next steps:"
echo "1. Review changes: git diff HEAD~1"
echo "2. Push to remote: git push origin main --tags"
echo "3. Update deployment configurations"
echo "4. Update CI/CD pipelines"
echo ""
echo "🎉 Saarathi is ready!"
