# LangFlix Frontend

React frontend for the LangFlix language learning platform.

## Features

- 🔐 User authentication (login/register)
- 📊 Dashboard with learning statistics
- 📚 Media library management
- 🔍 Expression search and browsing
- 🎬 Video streaming and playback
- 📱 Responsive design

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **React Router** - Client-side routing
- **TailwindCSS** - Styling
- **Axios** - HTTP client
- **Vite** - Build tool

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Copy environment variables:
   ```bash
   cp env.example .env
   ```

3. Update API URL in `.env` if needed:
   ```
   VITE_API_URL=http://localhost:8000
   ```

4. Start development server:
   ```bash
   npm run dev
   ```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Project Structure

```
src/
├── api/           # API client functions
├── components/    # Reusable components
├── context/       # React context providers
├── pages/         # Page components
├── hooks/         # Custom React hooks
└── App.tsx        # Main app component
```

## Development

The frontend connects to the LangFlix API backend. Make sure the backend is running on the configured API URL.

### Authentication Flow

1. User registers/logs in
2. JWT tokens are stored in localStorage
3. API requests include Authorization header
4. Automatic token refresh on 401 errors
5. Redirect to login on authentication failure

### Routing

- `/` - Landing page (public)
- `/login` - Login page (public)
- `/register` - Registration page (public)
- `/dashboard` - User dashboard (protected)
- `/library` - Media library (protected)
- `/upload` - Content upload (protected)

## Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.