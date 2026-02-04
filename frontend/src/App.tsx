import { Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import CreatePost from './pages/CreatePost';
import ApprovalQueue from './pages/ApprovalQueue';
import PostHistory from './pages/PostHistory';
import Settings from './pages/Settings';

function App() {
  return (
    <>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="create" element={<CreatePost />} />
          <Route path="queue" element={<ApprovalQueue />} />
          <Route path="history" element={<PostHistory />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </>
  );
}

export default App;
