const fs = require('fs');
const path = require('path');

/**
 * Get the BAXperience logo as base64 data URI for email embedding
 */
function getLogoDataUri() {
  try {
    const logoPath = path.join(__dirname, '../assets/baxperience-logo.png');
    const logoBuffer = fs.readFileSync(logoPath);
    const base64Logo = logoBuffer.toString('base64');
    return `data:image/png;base64,${base64Logo}`;
  } catch (error) {
    console.error('❌ Error loading logo:', error);
    return null;
  }
}

module.exports = {
  getLogoDataUri,
};
