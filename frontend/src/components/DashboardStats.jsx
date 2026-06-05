import React from 'react';
import { Database, Zap, Clock, ShieldCheck } from 'lucide-react';

export default function DashboardStats({ stats, recipeCount }) {
  const {
    cache = 'MISS',
    internalTime = 0,
    externalTime = 0,
    totalTime = 0,
  } = stats || {};

  return (
    <div className="dashboard-grid">
      <div className="stat-card">
        <div className="stat-card-title">
          <span className="stat-label">
            <Database size={16} /> Recipe Collection
          </span>
        </div>
        <div className="stat-card-value">{recipeCount}</div>
        <div className="stat-card-subtext">Total active internal recipes in database</div>
      </div>

      <div className="stat-card">
        <div className="stat-card-title">
          <span className="stat-label">
            <Zap size={16} /> Redis Cache Status
          </span>
        </div>
        <div className="stat-card-value" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span className={`cache-tag ${cache === 'HIT' ? 'hit' : 'miss'}`}>
            {cache}
          </span>
        </div>
        <div className="stat-card-subtext">Caching status for external API queries</div>
      </div>

      <div className="stat-card accent">
        <div className="stat-card-title">
          <span className="stat-label">
            <Clock size={16} /> Request Latency
          </span>
        </div>
        <div className="stat-card-value">
          {totalTime ? `${totalTime.toFixed(1)} ms` : 'N/A'}
        </div>
        <div className="stat-breakdown">
          <div className="stat-row">
            <span>SQLite lookup:</span>
            <span className="stat-value">{internalTime ? `${internalTime.toFixed(1)}ms` : '0ms'}</span>
          </div>
          <div className="stat-row">
            <span>TheMealDB API:</span>
            <span className="stat-value">{externalTime ? `${externalTime.toFixed(1)}ms` : '0ms'}</span>
          </div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-card-title">
          <span className="stat-label">
            <ShieldCheck size={16} /> System Health
          </span>
        </div>
        <div className="stat-card-value" style={{ fontSize: '1.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-success)' }}>
          Online
        </div>
        <div className="stat-card-subtext">All services functioning normally</div>
      </div>
    </div>
  );
}
