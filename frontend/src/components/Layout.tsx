import { Outlet, NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  PenSquare,
  CheckCircle,
  History,
  Settings,
  Zap,
} from 'lucide-react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/create', icon: PenSquare, label: 'Create Post' },
  { to: '/queue', icon: CheckCircle, label: 'Approval Queue' },
  { to: '/history', icon: History, label: 'Post History' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function Layout() {
  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 text-white flex flex-col">
        <div className="p-6 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <Zap className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-bold text-lg">Social Hub</h1>
              <p className="text-xs text-gray-400">Content Dashboard</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4">
          <ul className="space-y-1">
            {navItems.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                    }`
                  }
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="p-4 border-t border-gray-800">
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-sm text-gray-400">
              Powered by OpenAI
            </p>
            <p className="text-xs text-gray-500 mt-1">
              GPT-4o + DALL-E 3
            </p>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
