# Print Job Manager and Tracking System

A modular print job management and tracking program built on top of the copy-form functionality with a modern React-based web interface, real-time notifications, and role-based access control.

## Features

- **Dashboard**: Real-time statistics, job queue overview, and notifications
- **Queue Management**: View all jobs, filter by status, search, and bulk operations
- **Barcode Scanning**: Mobile camera support for tracking jobs via Code128 barcodes
- **User Management**: Authentication and role-based permissions (Admin, Manager, Staff, Submitter)
- **Real-time Notifications**: WebSocket-based push notifications with browser alerts
- **Direct Job Submission**: Submit jobs through web interface or Google Forms
- **Receipt Printing**: Thermal printer with embedded barcodes

## Tech Stack

### Frontend
- React 18+ with TypeScript
- Vite build tool
- Material-UI or Tailwind CSS
- Socket.IO client for real-time updates
- React Router v6

### Backend
- Flask with Flask-SocketIO
- Google Sheets API integration
- SQLite for user management
- JWT authentication
- Existing print processing logic

## Project Structure

```
print-job-manager/
├── backend/                # Flask backend
│   ├── src/               # Print processing logic
│   ├── api/               # API routes
│   ├── config/            # Configuration
│   ├── database/          # Database files
│   └── migrations/        # Database migrations
├── frontend/              # React frontend
├── docs/                  # Documentation
├── shared/                # Shared utilities
└── original-copy-form/    # Original codebase reference
```

## Development Status

🚧 **Currently in development** - Phase 1: Backend Foundation

## Getting Started

Documentation coming soon...

## License

Private project - All rights reserved
