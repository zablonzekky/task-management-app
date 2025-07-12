import React, { useState, useEffect, createContext, useContext } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import Components from "./Components";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchCurrentUser();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchCurrentUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem('token');
      delete axios.defaults.headers.common['Authorization'];
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, { username, password });
      const { access_token, user: userData } = response.data;
      
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      setUser(userData);
      
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || 'Login failed' };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

// Login Component
const Login = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const result = await login(username, password);
    
    if (!result.success) {
      setError(result.error);
    }
    
    setLoading(false);
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <Components.TaskManagerIcon />
          <h1>Task Manager</h1>
          <p>Sign in to your account</p>
        </div>
        
        <form onSubmit={handleLogin} className="login-form">
          {error && (
            <div className="error-alert">
              <Components.AlertIcon />
              {error}
            </div>
          )}
          
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="form-input"
              placeholder="Enter your username"
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="form-input"
              placeholder="Enter your password"
              required
            />
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="login-button"
          >
            {loading ? (
              <>
                <Components.LoadingIcon />
                Signing in...
              </>
            ) : (
              'Sign in'
            )}
          </button>
        </form>
        
        <div className="login-footer">
          <p>Default Admin: username=admin, password=admin123</p>
        </div>
      </div>
    </div>
  );
};

// Dashboard Component
const Dashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <Components.LoadingIcon />
        <p>Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Welcome back, {user?.full_name}</h1>
        <p>{user?.role === 'admin' ? 'Administrator Dashboard' : 'Your Tasks Overview'}</p>
      </div>
      
      <div className="stats-grid">
        {user?.role === 'admin' ? (
          <>
            <div className="stats-card stats-card-total">
              <div className="stats-content">
                <div className="stats-icon">
                  <Components.UsersIcon />
                </div>
                <div className="stats-text">
                  <h3>{stats.total_users || 0}</h3>
                  <p>Total Users</p>
                </div>
              </div>
            </div>
            
            <div className="stats-card stats-card-total">
              <div className="stats-content">
                <div className="stats-icon">
                  <Components.TasksIcon />
                </div>
                <div className="stats-text">
                  <h3>{stats.total_tasks || 0}</h3>
                  <p>Total Tasks</p>
                </div>
              </div>
            </div>
            
            <div className="stats-card stats-card-pending">
              <div className="stats-content">
                <div className="stats-icon">
                  <Components.PendingIcon />
                </div>
                <div className="stats-text">
                  <h3>{stats.pending_tasks || 0}</h3>
                  <p>Pending Tasks</p>
                </div>
              </div>
            </div>
            
            <div className="stats-card stats-card-progress">
              <div className="stats-content">
                <div className="stats-icon">
                  <Components.ProgressIcon />
                </div>
                <div className="stats-text">
                  <h3>{stats.in_progress_tasks || 0}</h3>
                  <p>In Progress</p>
                </div>
              </div>
            </div>
            
            <div className="stats-card stats-card-completed">
              <div className="stats-content">
                <div className="stats-icon">
                  <Components.CompletedIcon />
                </div>
                <div className="stats-text">
                  <h3>{stats.completed_tasks || 0}</h3>
                  <p>Completed</p>
                </div>
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="stats-card stats-card-total">
              <div className="stats-content">
                <div className="stats-icon">
                  <Components.TasksIcon />
                </div>
                <div className="stats-text">
                  <h3>{stats.my_tasks || 0}</h3>
                  <p>My Tasks</p>
                </div>
              </div>
            </div>
            
            <div className="stats-card stats-card-pending">
              <div className="stats-content">
                <div className="stats-icon">
                  <Components.PendingIcon />
                </div>
                <div className="stats-text">
                  <h3>{stats.pending_tasks || 0}</h3>
                  <p>Pending</p>
                </div>
              </div>
            </div>
            
            <div className="stats-card stats-card-progress">
              <div className="stats-content">
                <div className="stats-icon">
                  <Components.ProgressIcon />
                </div>
                <div className="stats-text">
                  <h3>{stats.in_progress_tasks || 0}</h3>
                  <p>In Progress</p>
                </div>
              </div>
            </div>
            
            <div className="stats-card stats-card-completed">
              <div className="stats-content">
                <div className="stats-icon">
                  <Components.CompletedIcon />
                </div>
                <div className="stats-text">
                  <h3>{stats.completed_tasks || 0}</h3>
                  <p>Completed</p>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

// Layout Component
const Layout = ({ children }) => {
  const { user, logout } = useAuth();
  const [currentPage, setCurrentPage] = useState('dashboard');

  return (
    <div className="app-layout">
      <nav className="sidebar">
        <div className="sidebar-header">
          <Components.TaskManagerIcon />
          <h2>Task Manager</h2>
        </div>
        
        <div className="nav-menu">
          <button
            onClick={() => setCurrentPage('dashboard')}
            className={`nav-item ${currentPage === 'dashboard' ? 'nav-item-active' : 'nav-item-inactive'}`}
          >
            <Components.DashboardIcon />
            Dashboard
          </button>
          
          <button
            onClick={() => setCurrentPage('tasks')}
            className={`nav-item ${currentPage === 'tasks' ? 'nav-item-active' : 'nav-item-inactive'}`}
          >
            <Components.TasksIcon />
            Tasks
          </button>
          
          {user?.role === 'admin' && (
            <button
              onClick={() => setCurrentPage('users')}
              className={`nav-item ${currentPage === 'users' ? 'nav-item-active' : 'nav-item-inactive'}`}
            >
              <Components.UsersIcon />
              Users
            </button>
          )}
        </div>
        
        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-avatar">
              {user?.full_name?.charAt(0).toUpperCase()}
            </div>
            <div className="user-details">
              <p className="user-name">{user?.full_name}</p>
              <p className="user-role">{user?.role}</p>
            </div>
          </div>
          <button onClick={logout} className="logout-button">
            <Components.LogoutIcon />
            Logout
          </button>
        </div>
      </nav>
      
      <main className="main-content">
        {currentPage === 'dashboard' && <Dashboard />}
        {currentPage === 'tasks' && <Components.TasksPage />}
        {currentPage === 'users' && user?.role === 'admin' && <Components.UsersPage />}
      </main>
    </div>
  );
};

// Main App Component
function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

const AppRoutes = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-container">
        <Components.LoadingIcon />
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/" replace /> : <Login />}
      />
      <Route
        path="/*"
        element={user ? <Layout /> : <Navigate to="/login" replace />}
      />
    </Routes>
  );
};

export default App;