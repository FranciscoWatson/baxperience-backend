# BAXperience API Gateway

API Gateway for the BAXperience tourism platform. This service acts as the main entry point for the React Native frontend and orchestrates communication with other microservices.

## Features

- User authentication (register/login)
- JWT-based authorization
- Itinerary management
- Rate limiting and security middleware
- Database integration with PostgreSQL

## Project Structure

```
src/
├── app.js              # Main application entry point
├── config/
│   └── database.js     # Database configuration and connection
├── controllers/
│   ├── authController.js     # Authentication logic
│   └── itineraryController.js # Itinerary management logic
├── middleware/
│   └── auth.js         # JWT authentication middleware
├── routes/
│   ├── auth.js         # Authentication routes
│   └── itinerary.js    # Itinerary routes
└── services/           # Business logic services (future expansion)
```

## Environment Setup

1. Copy `.env.example` to `.env` and configure your environment variables:
   ```bash
   cp .env.example .env
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Make sure your PostgreSQL database is running and properly configured.

## Available Scripts

- `npm start` - Start the production server
- `npm run dev` - Start the development server with nodemon

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/auth/profile` - Get user profile (requires auth)
- `POST /api/auth/profile/setup` - Setup user profile (after register)

### Itineraries
- `POST /api/itinerary` - Create new itinerary (requires auth)
- `GET /api/itinerary` - Get user's itineraries (requires auth)
- `GET /api/itinerary/:id` - Get specific itinerary (requires auth)
- `PUT /api/itinerary/:id` - Update itinerary (requires auth)
- `DELETE /api/itinerary/:id` - Delete itinerary (requires auth)

### Health Check
- `GET /health` - Service health status

## Security Features

- Helmet.js for security headers
- CORS configuration
- Rate limiting
- JWT authentication
- Input validation
- Password hashing with bcrypt

## Database Schema

The service expects these tables in the operational database:
- `users` - User account information
- `itineraries` - User itinerary data

## Development

This is a simple, focused implementation that can be expanded as needed. The structure supports easy addition of new controllers, services, and middleware.

For development, ensure your database connection is properly configured in the `.env` file.
