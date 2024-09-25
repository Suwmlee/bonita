// This file is auto-generated by @hey-api/openapi-ts

import type { CancelablePromise } from './core/CancelablePromise';
import { OpenAPI } from './core/OpenAPI';
import { request as __request } from './core/request';
import type { LoginAccessTokenData, LoginAccessTokenResponse, ReadUsersData, ReadUsersResponse, CreateUserData, CreateUserResponse, ReadUserMeResponse, DeleteUserMeResponse, UpdateUserMeData, UpdateUserMeResponse, UpdatePasswordMeData, UpdatePasswordMeResponse, RegisterUserData, RegisterUserResponse, ReadUserByIdData, ReadUserByIdResponse, UpdateUserData, UpdateUserResponse, DeleteUserData, DeleteUserResponse, RunTransferTaskData, RunTransferTaskResponse, GetTaskStatusData, GetTaskStatusResponse, GetAllTasksData, GetAllTasksResponse, CreateTaskData, CreateTaskResponse, UpdateTaskData, UpdateTaskResponse, GetAllSettingsData, GetAllSettingsResponse, CreateSettingData, CreateSettingResponse, UpdateSettingData, UpdateSettingResponse, DeleteSettingData, DeleteSettingResponse } from './types.gen';

export class LoginService {
    /**
     * 获取token
     * 获取认证Token
     * @param data The data for the request.
     * @param data.formData
     * @returns Token Successful Response
     * @throws ApiError
     */
    public static loginAccessToken(data: LoginAccessTokenData): CancelablePromise<LoginAccessTokenResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/login/access-token',
            formData: data.formData,
            mediaType: 'application/x-www-form-urlencoded',
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
}

export class UserService {
    /**
     * Read Users
     * Retrieve users.
     * @param data The data for the request.
     * @param data.skip
     * @param data.limit
     * @returns UsersPublic Successful Response
     * @throws ApiError
     */
    public static readUsers(data: ReadUsersData = {}): CancelablePromise<ReadUsersResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/users/',
            query: {
                skip: data.skip,
                limit: data.limit
            },
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Create User
     * Create new user.
     * @param data The data for the request.
     * @param data.requestBody
     * @returns UserPublic Successful Response
     * @throws ApiError
     */
    public static createUser(data: CreateUserData): CancelablePromise<CreateUserResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/users/',
            body: data.requestBody,
            mediaType: 'application/json',
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Read User Me
     * Get current user.
     * @returns UserPublic Successful Response
     * @throws ApiError
     */
    public static readUserMe(): CancelablePromise<ReadUserMeResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/users/me'
        });
    }
    
    /**
     * Delete User Me
     * Delete own user.
     * @returns Response Successful Response
     * @throws ApiError
     */
    public static deleteUserMe(): CancelablePromise<DeleteUserMeResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/users/me'
        });
    }
    
    /**
     * Update User Me
     * Update own user.
     * @param data The data for the request.
     * @param data.requestBody
     * @returns UserPublic Successful Response
     * @throws ApiError
     */
    public static updateUserMe(data: UpdateUserMeData): CancelablePromise<UpdateUserMeResponse> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/users/me',
            body: data.requestBody,
            mediaType: 'application/json',
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Update Password Me
     * Update own password.
     * @param data The data for the request.
     * @param data.requestBody
     * @returns Response Successful Response
     * @throws ApiError
     */
    public static updatePasswordMe(data: UpdatePasswordMeData): CancelablePromise<UpdatePasswordMeResponse> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/users/me/password',
            body: data.requestBody,
            mediaType: 'application/json',
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Register User
     * Create new user without the need to be logged in.
     * @param data The data for the request.
     * @param data.requestBody
     * @returns UserPublic Successful Response
     * @throws ApiError
     */
    public static registerUser(data: RegisterUserData): CancelablePromise<RegisterUserResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/users/signup',
            body: data.requestBody,
            mediaType: 'application/json',
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Read User By Id
     * Get a specific user by id.
     * @param data The data for the request.
     * @param data.userId
     * @returns UserPublic Successful Response
     * @throws ApiError
     */
    public static readUserById(data: ReadUserByIdData): CancelablePromise<ReadUserByIdResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/users/{user_id}',
            path: {
                user_id: data.userId
            },
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Update User
     * Update a user.
     * @param data The data for the request.
     * @param data.userId
     * @param data.requestBody
     * @returns UserPublic Successful Response
     * @throws ApiError
     */
    public static updateUser(data: UpdateUserData): CancelablePromise<UpdateUserResponse> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/users/{user_id}',
            path: {
                user_id: data.userId
            },
            body: data.requestBody,
            mediaType: 'application/json',
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Delete User
     * Delete a user.
     * @param data The data for the request.
     * @param data.userId
     * @returns Response Successful Response
     * @throws ApiError
     */
    public static deleteUser(data: DeleteUserData): CancelablePromise<DeleteUserResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/users/{user_id}',
            path: {
                user_id: data.userId
            },
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
}

export class TaskService {
    /**
     * Run Transfer Task
     * 立即执行任务
     * @param data The data for the request.
     * @param data.id
     * @returns TaskBase Successful Response
     * @throws ApiError
     */
    public static runTransferTask(data: RunTransferTaskData): CancelablePromise<RunTransferTaskResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/task/run/{id}',
            path: {
                id: data.id
            },
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Get Task Status
     * 查看任务状态
     * @param data The data for the request.
     * @param data.taskId
     * @returns TaskStatus Successful Response
     * @throws ApiError
     */
    public static getTaskStatus(data: GetTaskStatusData): CancelablePromise<GetTaskStatusResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/task/{task_id}',
            path: {
                task_id: data.taskId
            },
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
}

export class TransferTaskService {
    /**
     * Get All Tasks
     * 获取所有任务配置
     * @param data The data for the request.
     * @param data.skip
     * @param data.limit
     * @returns TransferTasksPublic Successful Response
     * @throws ApiError
     */
    public static getAllTasks(data: GetAllTasksData = {}): CancelablePromise<GetAllTasksResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/tasks/transfer/all',
            query: {
                skip: data.skip,
                limit: data.limit
            },
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Create Task
     * 创建新任务配置
     * @param data The data for the request.
     * @param data.requestBody
     * @returns TransferTaskPublic Successful Response
     * @throws ApiError
     */
    public static createTask(data: CreateTaskData): CancelablePromise<CreateTaskResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/tasks/transfer/',
            body: data.requestBody,
            mediaType: 'application/json',
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Update Task
     * 更新任务配置
     * @param data The data for the request.
     * @param data.id
     * @param data.requestBody
     * @returns TransferTaskPublic Successful Response
     * @throws ApiError
     */
    public static updateTask(data: UpdateTaskData): CancelablePromise<UpdateTaskResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/tasks/transfer/{id}',
            path: {
                id: data.id
            },
            body: data.requestBody,
            mediaType: 'application/json',
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
}

export class ScrapingSettingService {
    /**
     * Get All Settings
     * 获取所有配置.
     * @param data The data for the request.
     * @param data.skip
     * @param data.limit
     * @returns ScrapingSettingsPublic Successful Response
     * @throws ApiError
     */
    public static getAllSettings(data: GetAllSettingsData = {}): CancelablePromise<GetAllSettingsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/scraping/settings/all',
            query: {
                skip: data.skip,
                limit: data.limit
            },
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Create Setting
     * 创建新配置
     * @param data The data for the request.
     * @param data.requestBody
     * @returns ScrapingSettingPublic Successful Response
     * @throws ApiError
     */
    public static createSetting(data: CreateSettingData): CancelablePromise<CreateSettingResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/scraping/settings/',
            body: data.requestBody,
            mediaType: 'application/json',
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Update Setting
     * Update an setting.
     * @param data The data for the request.
     * @param data.id
     * @param data.requestBody
     * @returns ScrapingSettingPublic Successful Response
     * @throws ApiError
     */
    public static updateSetting(data: UpdateSettingData): CancelablePromise<UpdateSettingResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/scraping/settings/{id}',
            path: {
                id: data.id
            },
            body: data.requestBody,
            mediaType: 'application/json',
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Delete Setting
     * Delete an setting.
     * @param data The data for the request.
     * @param data.id
     * @returns Response Successful Response
     * @throws ApiError
     */
    public static deleteSetting(data: DeleteSettingData): CancelablePromise<DeleteSettingResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/scraping/settings/{id}',
            path: {
                id: data.id
            },
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
}