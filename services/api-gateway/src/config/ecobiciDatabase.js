const { Pool } = require('pg');

class EcobiciDatabaseService {
  constructor() {
    this.pool = new Pool({
      host: process.env.ECOBICI_DB_HOST || 'localhost',
      port: process.env.ECOBICI_DB_PORT || 5432,
      database: process.env.ECOBICI_DB_NAME || 'eco_bicis',
      user: process.env.ECOBICI_DB_USER || 'postgres',
      password: process.env.ECOBICI_DB_PASSWORD || 'admin',
      max: 10,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 2000,
    });
  }

  async query(text, params) {
    const start = Date.now();
    const client = await this.pool.connect();
    
    try {
      const res = await client.query(text, params);
      return res;
    } finally {
      client.release();
    }
  }

  async getClient() {
    return await this.pool.connect();
  }

  async close() {
    await this.pool.end();
  }
}

module.exports = new EcobiciDatabaseService();






