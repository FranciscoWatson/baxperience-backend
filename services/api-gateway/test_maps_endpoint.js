/**
 * Test Script for Google Maps API Endpoint
 * 
 * This script tests the /api/maps/config endpoint
 * Make sure the API Gateway is running before executing this script
 */

const API_BASE_URL = 'http://localhost:3000';

// Replace with a valid JWT token from your authentication
const AUTH_TOKEN = 'your_jwt_token_here';

async function testMapsConfig() {
  console.log('🧪 Testing Google Maps Config Endpoint\n');
  console.log(`📡 URL: ${API_BASE_URL}/api/maps/config\n`);

  try {
    const response = await fetch(`${API_BASE_URL}/api/maps/config`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${AUTH_TOKEN}`,
        'Content-Type': 'application/json',
      },
    });

    console.log(`📊 Status: ${response.status} ${response.statusText}\n`);

    const data = await response.json();
    
    if (response.ok) {
      console.log('✅ Success! Maps configuration retrieved:\n');
      console.log({
        ...data,
        apiKey: data.apiKey ? `${data.apiKey.substring(0, 10)}...` : 'NOT SET'
      });
      console.log('\n🎉 Google Maps API Key is configured correctly!\n');
      
      // Test if it's a valid key format (basic check)
      if (data.apiKey && data.apiKey.length > 20) {
        console.log('✓ API Key format looks valid');
      } else {
        console.log('⚠️  Warning: API Key might be invalid');
      }
    } else {
      console.log('❌ Error:', data);
      
      if (response.status === 401) {
        console.log('\n⚠️  Authentication failed. Make sure to:');
        console.log('   1. Replace AUTH_TOKEN with a valid JWT token');
        console.log('   2. Login first and use the token from the response');
      } else if (response.status === 500) {
        console.log('\n⚠️  Server error. Make sure to:');
        console.log('   1. Set GOOGLE_MAPS_API_KEY in the .env file');
        console.log('   2. Restart the API Gateway server');
      }
    }
  } catch (error) {
    console.error('❌ Network Error:', error.message);
    console.log('\n⚠️  Make sure:');
    console.log('   1. The API Gateway is running (npm run dev)');
    console.log('   2. The URL is correct:', API_BASE_URL);
  }
}

// Helper function to login and get a token (if you have test credentials)
async function loginAndGetToken(email, password) {
  console.log('🔐 Logging in to get authentication token...\n');
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();
    
    if (response.ok && data.token) {
      console.log('✅ Login successful!\n');
      return data.token;
    } else {
      console.log('❌ Login failed:', data);
      return null;
    }
  } catch (error) {
    console.error('❌ Login error:', error.message);
    return null;
  }
}

// Main execution
async function main() {
  console.log('═══════════════════════════════════════════════════════════');
  console.log('  Google Maps API Endpoint Test');
  console.log('═══════════════════════════════════════════════════════════\n');

  // Option 1: If you have test credentials, uncomment and use:
  // const email = 'test@example.com';
  // const password = 'testpassword123';
  // const token = await loginAndGetToken(email, password);
  // if (token) {
  //   AUTH_TOKEN = token;
  // }

  // Option 2: Test with the token from AUTH_TOKEN constant
  if (AUTH_TOKEN === 'your_jwt_token_here') {
    console.log('⚠️  Please set a valid JWT token in the AUTH_TOKEN constant\n');
    console.log('You can get a token by:');
    console.log('1. Logging in through your app');
    console.log('2. Checking the network tab in dev tools');
    console.log('3. Copying the token from the login response\n');
    console.log('Or uncomment the login code above with test credentials.\n');
    return;
  }

  await testMapsConfig();
  
  console.log('\n═══════════════════════════════════════════════════════════');
}

// Run the test
main();
