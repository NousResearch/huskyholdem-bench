import { createBrowserRouter, RouterProvider } from "react-router-dom";
import "./App.css";
import Home from "./page/Home";
import Register from "./page/Register";
import Login from "./page/Login";
import About from "./page/About";
import { AuthProvider } from "./context/AuthContext";
import Dashboard from "./page/Dashboard";
import ProtectedRoute from "./components/ProtectedRoute";
import SubmissionPage from "./page/Submission";
import ProfilePage from "./page/Profile"
import VerificationSuccess from "./page/VerificationSuccess";
import LeaderboardPage from "./page/Leaderboard";
import Admin from "./page/Admin";
import SimulationPage from "./page/Simulation";
import DirectoryPage from "./page/Directory";
import VerifyAccount from "./page/VerifyAccount";
import VerifiedRoute from "./components/VerifiedRoute";
import VerifiedAdminRoute from "./components/VerifiedAdminRoute";
import ContainerManagerPage from "./page/ContainerManager";
import GamePage from "./page/Game";
import JobGamesPage from "./page/JobGames";
import Replay from "./page/Replay";
import UploadReplay from "./page/UploadReplay";
import DefaultLayout from "./layout/index";
import AdminGamePage from "./page/AdminGame";

function App() {
  const router = createBrowserRouter([
    {
      path: "/",
      element: (
        <DefaultLayout>
          <Home />
        </DefaultLayout>
      ),
    },
    {
      path: "/register",
      element: (
        <DefaultLayout>
          <Register />
        </DefaultLayout>
      ),
    },

    {
      path: "/login",
      element: (
        <DefaultLayout>
          <Login />
        </DefaultLayout>
      ),
    },
    {
      path: "/verification-success",
      element: (
        <DefaultLayout>
          <VerificationSuccess />
        </DefaultLayout>
      ),
    },
    {
      path: "/verify-account",
      element: (
        <ProtectedRoute>
          <DefaultLayout>
            <VerifyAccount />
          </DefaultLayout>
        </ProtectedRoute>
      ),
    },
    {
      path: "/about",
      element: (
        <DefaultLayout>
          <About />
        </DefaultLayout>
      ),
      },
      {
        path: "/dashboard",
          element: (
        <VerifiedRoute>              
            <DefaultLayout>
                <Dashboard />
            </DefaultLayout>
        </VerifiedRoute>
        ),
    },
    {
      path: "/submission",
        element: (
      <VerifiedRoute>              
          <DefaultLayout>
              <SubmissionPage  />
          </DefaultLayout>
      </VerifiedRoute>
      ),
    },
    {
      path: "/leaderboard",
        element: (
      <VerifiedRoute>              
          <DefaultLayout>
              <LeaderboardPage  />
          </DefaultLayout>
      </VerifiedRoute>
      ),
    },
    {
      path: "/games",
        element: (
          <DefaultLayout>
              <GamePage  />
          </DefaultLayout>
      ),
    },
    {
      path: "/games/:jobId",
      element: (
          <DefaultLayout>
            <JobGamesPage />
          </DefaultLayout>
      ),
    },
    {
      path: "/directory",
        element: (
      <VerifiedRoute>              
          <DefaultLayout>
              <DirectoryPage  />
          </DefaultLayout>
      </VerifiedRoute>
      ),
    },
    {
      path: "/profile",
        element: (
      <VerifiedRoute>              
            <DefaultLayout>
              <ProfilePage  />
          </DefaultLayout>
      </VerifiedRoute>
      ),
    },  
    {
      path: "/profile/:username",
      element: (
        <DefaultLayout>
          <ProfilePage />
        </DefaultLayout>
      ),
    },
    {
      path: "/admin",
      element: (
        <VerifiedAdminRoute>
          <DefaultLayout>
            <Admin />
          </DefaultLayout>
        </VerifiedAdminRoute>
      ),
    },
    {
      path: "/simulation",
      element: (
        <VerifiedAdminRoute>              
            <DefaultLayout>
                <SimulationPage  />
            </DefaultLayout>
        </VerifiedAdminRoute>
      ),
    },
    {
      path: "/container-manager",
      element: (
        <VerifiedAdminRoute>              
            <DefaultLayout>
                <ContainerManagerPage  />
            </DefaultLayout>
        </VerifiedAdminRoute>
      ),
    },
    {
      path: "/admin/games",
      element: (
        <VerifiedAdminRoute>
          <DefaultLayout>
            <AdminGamePage />
          </DefaultLayout>
        </VerifiedAdminRoute>
      ),
    },
    {
      path: "/replay/:gameId",
      element: (
        <DefaultLayout>
          <Replay />
        </DefaultLayout>
      ),
    },
    {
      path: "/upload-replay",
      element: (
        <DefaultLayout>
          <UploadReplay />
        </DefaultLayout>
      ),
    },
  ]);

  return (
      <>
          <AuthProvider>  
            <RouterProvider router={router} />
          </AuthProvider>
    </>
  );
}

export default App;
