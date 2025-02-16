# VisuLinx API

A FastAPI-based application designed for understanding documents and images, using multimodal LLMs to detect and locate objects within these images through precise bounding box detection.

## 🎯 Core Purpose

- **Document Processing**: Extract and manage images from various document formats
- **AI-Powered Analysis**: Leverage multiple AI providers (Gemini, Together AI, Hyperbolic) for accurate object detection
- **Multi-Organization Support**: Organize and manage documents across different organizations and projects
- **Secure Access**: Role-based access control with organization-level permissions

## 🚀 Features

- **User Management**: Secure user authentication and authorization
- **Organization Management**: Create and manage organizations with multiple users
- **Project Management**: Organize work into projects within organizations
- **File Processing**: Handle file uploads with S3 integration
- **Preferences System**: Flexible system-wide preferences management
- **RESTful API**: Modern, fast, and well-documented API endpoints
- **CORS Support**: Configured for cross-origin resource sharing

## 🏗 Project Structure

```
app/
├── api.py              # FastAPI application configuration
├── database.py         # Database connection and settings
├── models.py           # SQLAlchemy ORM models
├── routers/           # API route handlers
├── schemas.py         # Pydantic models for request/response
├── security.py        # Authentication and authorization
├── services/         # Business logic services
└── settings.py        # Application settings
```

## 🔧 Technical Stack

- **Framework**: FastAPI
- **Database**: SQLAlchemy ORM
- **Authentication**: JWT-based authentication
- **Storage**: AWS S3 integration
- **Data Validation**: Pydantic
- **API Documentation**: Automatic OpenAPI/Swagger docs

## 💻 Key Components

### Models
- **User**: Manages user accounts and authentication
- **Organization**: Handles multi-user organizations
- **Project**: Organizes work within organizations
- **File**: Manages file uploads and processing
- **Preference**: Stores system-wide preferences

### API Endpoints
- `/users`: User management endpoints
- `/auth`: Authentication endpoints
- `/organizations`: Organization management
- `/projects`: Project-related operations
- `/preferences`: System preferences management

### 🤖 AI Services

The project integrates with multiple AI providers for advanced image analysis and object detection:

#### Supported AI Providers
- **Together AI**: Uses the Qwen2-VL-72B-Instruct model for high-quality visual analysis
- **Hyperbolic AI**: Implements the same Qwen model through a different API endpoint
- **Google Gemini**: Utilizes Gemini 1.5 Pro for advanced image processing

#### Features
- **Object Detection**: Extract bounding boxes for objects in images
- **Image Processing**: Automatic image resizing and compression for optimal AI processing
- **Multi-Provider Support**: Fallback options across different AI services
- **Standardized Interface**: Consistent API across all providers through the `AiService` abstract base class

#### Configuration
The AI services require the following environment variables:
```
GOOGLE_API_KEY=     # For Gemini AI
TOGETHER_API_KEY=   # For Together AI
HYPERBOLIC_API_KEY= # For Hyperbolic AI
```

## 🔒 Security Features

- Secure password hashing
- JWT token-based authentication
- Role-based access control
- CORS middleware configuration

## 🚀 Getting Started

### Prerequisites

- Python >= 3.13
- uv (Python package installer)

### Installation

1. Clone the repository
2. Install dependencies using uv:
   ```bash
   uv sync
   ```
3. Configure environment variables
4. Run the application:
   ```bash
   uv run fastapi dev
   ```

## 📝 API Documentation

Once the server is running, access the API documentation at:
- Swagger UI: `http://localhost:8000/docs`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

MIT License

## Autogenerate migration

```sh
uv run alembic revision --autogenerate -m "add ... table"
```

## Generating secrets

```sh
python -c "import secrets; print(secrets.token_urlsafe(32))"

```
