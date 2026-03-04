# Print Job Manager Frontend

React + TypeScript + Vite frontend for the Print Job Manager system.

## Quick Start

### Prerequisites
- Node.js 18+ and npm

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

The app will be available at http://localhost:3000

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Features

- **Dashboard**: Real-time job statistics
- **Queue Manager**: View and filter all jobs
- **Barcode Scanner**: Scan or enter job IDs to update status
- **Admin Panel**: User and system management (Admin only)
- **Real-Time Updates**: WebSocket integration for live updates

## Tech Stack

- React 18.2
- TypeScript
- Vite
- Material-UI (MUI)
- Redux Toolkit
- Socket.IO Client
- Axios
- React Router v6

## Project Structure

```
src/
├── components/          # React components
│   ├── Dashboard/      # Dashboard component
│   ├── QueueManager/   # Job queue management
│   ├── Scanner/        # Barcode scanner
│   ├── AdminPanel/     # Admin interface
│   └── common/         # Shared components (Layout, ProtectedRoute)
├── services/           # API and WebSocket services
│   ├── api.ts          # Axios API client
│   ├── auth.ts         # Authentication service
│   ├── jobs.ts         # Job management service
│   └── websocket.ts    # WebSocket service
├── store/              # Redux store
│   ├── store.ts        # Store configuration
│   ├── authSlice.ts    # Auth state management
│   └── jobsSlice.ts    # Jobs state management
├── types/              # TypeScript type definitions
├── config.ts           # App configuration
├── App.tsx             # Main app component
└── main.tsx            # Entry point
```

## Environment Variables

Create a `.env` file:

```env
VITE_API_URL=http://localhost:5000/api
VITE_WS_URL=http://localhost:5000
```

## API Integration

The frontend connects to the backend API at `http://localhost:5000/api`.

Make sure the backend server is running before starting the frontend:

```bash
cd ../backend
source venv/bin/activate
python3 api/app.py
```

## Default Login

- Username: `admin`
- Password: `admin123`

⚠️ Change this immediately in production!

## Development Notes

- The app uses Material-UI for the component library
- Redux Toolkit manages global state
- Socket.IO provides real-time updates
- Axios handles HTTP requests with automatic token refresh
- Protected routes check authentication and user roles

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

Private project - All rights reserved
