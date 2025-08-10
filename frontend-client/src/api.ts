import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'https://api-huskyholdem.atcuw.org',
//   baseURL: 'http://localhost:8002',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds timeout
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      // Handle unauthorized access
      console.error('Unauthorized access - redirecting to login');
      // Redirect to login page or show a modal
    }
    return Promise.reject(error);
  }
);

const authAPI = {
    login: async (username: string, password: string) => {
        const response = await apiClient.post('/auth/login', { username, password });
        return response.data;
    },
    register: async (username: string, email: string, password: string) => {
        const response = await apiClient.post('/auth/register', {
            username,
            email,
            password,
        });
        return response.data;
    },
    verify: async (token: string) => {
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        const response = await apiClient.get('/auth/whoami');
        return response.data;
    },
    logout: async (token: string) => {
        const response = await apiClient.post('/auth/logout', { token });
        return response.data;
    },
    resendVerification: async () => {
        const response = await apiClient.post('/auth/resend-verification');
        return response.data;
    }
}

const liveAPI = {
    get_all_job_ids: async () => {
        const response = await apiClient.get('/live/job-ids');
        return response.data;
    },
    get_public_job_ids: async () => {
        const response = await apiClient.get('/live/public-job-ids');
        return response.data;
    },
    get_job_games: async (job_id: string) => {
        const response = await apiClient.get(`/live/job/${job_id}/games`);
        return response.data;
    },
    get_game_data: async (game_id: string) => {
        const response = await apiClient.get(`/live/game/${game_id}`);
        return response.data;
    },
    get_user_performance: async (job_id: string) => {
        const response = await apiClient.get(`/live/job/${job_id}/user-performance`);
        return response.data;
    },
}

const gameAPI = {
    get_jobs: async () => {
        const response = await apiClient.get('/sim/status/all');
        return response.data;
    },
    get_job: async (job_id: string) => {
        const response = await apiClient.get(`/sim/status/${job_id}`);
        return response.data;
    },

    submitSimulationJob: async (formData: FormData) => {
        const response = await apiClient.post("/sim/async_run", formData, {
        headers: {
            "Content-Type": "multipart/form-data",
        },
        });

        if (response.data.status_code !== 200) {
            throw new Error(response.data.error);
        }
        return response.data;
    },
    submitSimulationUserJob: async (
        usernames: string[],
        numRounds: number = 6,
        blind: number = 10,
        blindMultiplier: number = 1.0,
        blindIncreaseInterval: number = 1
      ) => {
          const payload = {
              users_list: usernames,
              num_rounds: numRounds,
              blind,
              blind_multiplier: blindMultiplier,
              blind_increase_interval: blindIncreaseInterval
          };
        const response = await apiClient.post("/sim/async_run_user", payload);
      
        if (response.data.status_code !== 200) {
          throw new Error(response.data.error);
        }
        return response.data;
      },
    deleteJob: async (job_id: string) => {
        const response = await apiClient.delete(`/sim/job/${job_id}`);
        return response.data;
    }
}

const submissionAPI = {
   uploadSubmission: async (formData: FormData) => {
        const response = await apiClient.post("/submission/upload", formData, {
        headers: {
            "Content-Type": "multipart/form-data",
        },
        });

        if (response.data.status_code !== 200) {
            throw new Error(response.data.error);
        }
        return response.data;
      },
    getSubmission: async (submission_id: string) => {
        const res = await apiClient.get(`/submission/list`);
        const submission = res.data.files.find((file: any) => file.id === submission_id);
        return submission;
    },
    getContentFile: async (file_name: string) => {
        const res = await apiClient.get(`/submission/files/${file_name}`);
        return res.data; 
    },
    listSubmissions: async () => {
        const response = await apiClient.get('/submission/list');
        console.log(response.data)
        return response.data;
    },
    unmark_submission: async (submission_id: string) => {
        const response = await apiClient.post(`/submission/unmark_final`, { 
            submission_id: submission_id
         });
        return response.data;
    },
    mark_submission: async (submission_id: string) => {
        const response = await apiClient.post(`/submission/mark_final`, { 
            submission_id: submission_id
         });
        return response.data;
    },
    delete_submission: async (submission_id: string) => {
        const response = await apiClient.delete(`/submission/${submission_id}`);
        return response.data;
    },
    getUsersWithFinalSubmission: async () => {
        const response = await apiClient.get('/submission/users/with-final')
        return response.data
    }
}

const profileAPI = {
    getProfilePublic: async (username: string) => {
        const res = await apiClient.get(`/profile/${username}`);
        return res.data;
    },

    getProfileSelf: async () => {
        const res = await apiClient.get(`/profile`);
        return res.data;
    },

    updateProfile: async (data: {
        name?: string;
        github?: string;
        discord_username?: string;
        about?: string;
    }) => {
        const res = await apiClient.post('/user/update', data);
        return res.data;
    },
}

const leaderboardAPI = {
    getTopN: async (n: number, tag?: string) => {
        const params = tag ? `?tag=${encodeURIComponent(tag)}` : '';
        const response = await apiClient.get(`/leaderboard/top/${n}${params}`);
        return response.data;
    },
    
    getAllTags: async () => {
        const response = await apiClient.get('/leaderboard/tags');
        return response.data;
    },
    
    getUserEntries: async (username: string, tag?: string) => {
        const params = tag ? `?tag=${encodeURIComponent(tag)}` : '';
        const response = await apiClient.get(`/leaderboard/user/${username}${params}`);
        return response.data;
    },
    
    removeEntry: async (entryId: string) => {
        const response = await apiClient.delete(`/leaderboard/remove/${entryId}`);
        return response.data;
    },
    
    addEntry: async (score: number, tag?: string) => {
        const response = await apiClient.post('/leaderboard/add', { score, tag });
        return response.data;
    }
}

const userAPI = {
    getAllUsers: async (page: number = 1, pageSize: number = 25) => {
        const res = await apiClient.get(`/user/all?page=${page}&page_size=${pageSize}`);
        return res.data
    },
    searchUsers: async (query: string) => {
        const res = await apiClient.get(`/user/search?q=${encodeURIComponent(query)}`);
        return res.data;
    }
}

const adminAPI = {
    getUserCount: async () => {
        const res = await apiClient.get('/admin/user-count');
        return res.data.user_count;
    },
    getJobCount: async () => {
        const res = await apiClient.get('/admin/job-count');
        return res.data.job_count;
    },
    getSubmissionCount: async () => {
        const res = await apiClient.get('/admin/submission-count');
        return res.data.submission_count;
    },
    listUsers: async () => {
        const res = await apiClient.get('/admin/users');
        return res.data;
    },
    listJobs: async () => {
        const res = await apiClient.get('/admin/jobs');
        return res.data;
    },
    toggleAdmin: async (username: string) => {
        const res = await apiClient.post(`/admin/toggle-admin/${username}`);
        return res.data;
    },
    verifyUser: async (username: string) => {
        const res = await apiClient.post(`/admin/verify-user/${username}`);
        return res.data;
    },
    deleteUser: async (username: string) => {
        const res = await apiClient.delete(`/admin/user/${username}`);
        return res.data;
    },
    listSimAdminJob: async () => {
        const res = await apiClient.get('/admin/sim-admin-jobs');
        return res.data;
    },
    listScalingJob: async () => {
        const res = await apiClient.get('/admin/scaling-jobs');
        return res.data;
    },
    toggleJobPublic: async (job_id: string) => {
        const res = await apiClient.post(`/admin/toggle-job-public/${job_id}`);
        return res.data;
    },
    get2025JobStatus: async (job_id: string) => {
        const res = await apiClient.get(`/admin/2025-job-status/${job_id}`);
        return res.data;
    },
    processTournament2025Job: async (job_id: string) => {
        const res = await apiClient.post(`/admin/process-tournament-2025-job/${job_id}`);
        return res.data;
    },
    deleteTournament2025Job: async (job_id: string) => {
        const res = await apiClient.post(`/admin/delete-tournament-2025-job/${job_id}`);
        return res.data;
    },
    getUserFinalSubmission: async (username: string) => {
        const res = await apiClient.get(`/admin/user-final-submission/${username}`);
        return res.data;
    }
}

const dockerAPI = {
    getPoolStatus: async () => {
        const res = await apiClient.get('/docker/pool/status');
        return res.data
    },
    getPoolDetailed: async () => {
        const res = await apiClient.get('/docker/pool/detailed');
        return res.data;
    },
    submitScalingJob: async (targetSize: number) => {
        const response = await apiClient.post(`/docker/pool/scale?target_size=${targetSize}`);
    
        if (response.status !== 200) {
            throw new Error(response.data?.detail || 'Failed to scale pool');
        }
    
        return response.data;
    },
    getGameLog: async (port: number) => {
        const response = await apiClient.get(`/docker/game-log/${port}`);
        return response.data;
    }
};

export {
    apiClient,
    authAPI,
    gameAPI,
    submissionAPI,
    profileAPI,
    leaderboardAPI,
    userAPI,
    adminAPI,
    dockerAPI,
    liveAPI
}