// This file is auto-generated by @hey-api/openapi-ts

import type { CancelablePromise } from './core/CancelablePromise';
import { OpenAPI } from './core/OpenAPI';
import { request as __request } from './core/request';
import type { LoginAccessTokenData, LoginAccessTokenResponse, ReadUsersData, ReadUsersResponse, CreateUserData, CreateUserResponse, ReadUserMeResponse, DeleteUserMeResponse, UpdateUserMeData, UpdateUserMeResponse, UpdatePasswordMeData, UpdatePasswordMeResponse, RegisterUserData, RegisterUserResponse, ReadUserByIdData, ReadUserByIdResponse, UpdateUserData, UpdateUserResponse, DeleteUserData, DeleteUserResponse, RunTransferTaskData, RunTransferTaskResponse, GetTaskStatusData, GetTaskStatusResponse, GetAllTasksData, GetAllTasksResponse, CreateTaskData, CreateTaskResponse, UpdateTaskData, UpdateTaskResponse, DeleteTaskData, DeleteTaskResponse, GetAllSettingsData, GetAllSettingsResponse, CreateSettingData, CreateSettingResponse, UpdateSettingData, UpdateSettingResponse, DeleteSettingData, DeleteSettingResponse, GetRecordsData, GetRecordsResponse, UpdateRecordData, UpdateRecordResponse, GetTransRecordsData, GetTransRecordsResponse, GetMetadataData, GetMetadataResponse, UpdateMetadataData, UpdateMetadataResponse, DeleteMetadataData, DeleteMetadataResponse, GetImageByQueryData, GetImageByQueryResponse, UploadImageData, UploadImageResponse } from './types.gen';

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
    
    /**
     * Delete Task
     * Delete an task.
     * @param data The data for the request.
     * @param data.id
     * @returns Response Successful Response
     * @throws ApiError
     */
    public static deleteTask(data: DeleteTaskData): CancelablePromise<DeleteTaskResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/tasks/transfer/{id}',
            path: {
                id: data.id
            },
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

export class TransRecordsService {
    /**
     * Get Records
     * 获取记录信息 包含 ExtraInfo
     * @param data The data for the request.
     * @param data.skip
     * @param data.limit
     * @returns RecordsPublic Successful Response
     * @throws ApiError
     */
    public static getRecords(data: GetRecordsData = {}): CancelablePromise<GetRecordsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/records/all',
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
     * Update Record
     * 更新记录信息 包含 ExtraInfo
     * @param data The data for the request.
     * @param data.requestBody
     * @returns RecordPublic Successful Response
     * @throws ApiError
     */
    public static updateRecord(data: UpdateRecordData): CancelablePromise<UpdateRecordResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/records/record',
            body: data.requestBody,
            mediaType: 'application/json',
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Get Trans Records
     * @param data The data for the request.
     * @param data.skip
     * @param data.limit
     * @returns TransferRecordsPublic Successful Response
     * @throws ApiError
     */
    public static getTransRecords(data: GetTransRecordsData = {}): CancelablePromise<GetTransRecordsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/records/transrecords',
            query: {
                skip: data.skip,
                limit: data.limit
            },
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
}

export class MetadataService {
    /**
     * Get Metadata
     * 获取元数据
     * @param data The data for the request.
     * @param data.skip
     * @param data.limit
     * @returns MetadataCollection Successful Response
     * @throws ApiError
     */
    public static getMetadata(data: GetMetadataData = {}): CancelablePromise<GetMetadataResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/metadata/all',
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
     * Update Metadata
     * 更新元数据
     *
     * Args:
     * session: 数据库会话
     * id: 元数据ID
     * metadata: 更新的元数据内容
     *
     * Returns:
     * 更新后的元数据
     * @param data The data for the request.
     * @param data.id
     * @param data.requestBody
     * @returns MetadataPublic Successful Response
     * @throws ApiError
     */
    public static updateMetadata(data: UpdateMetadataData): CancelablePromise<UpdateMetadataResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/metadata/{id}',
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
     * Delete Metadata
     * 删除元数据
     *
     * Args:
     * session: 数据库会话
     * id: 元数据ID
     * @param data The data for the request.
     * @param data.id
     * @returns Response Successful Response
     * @throws ApiError
     */
    public static deleteMetadata(data: DeleteMetadataData): CancelablePromise<DeleteMetadataResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/metadata/{id}',
            path: {
                id: data.id
            },
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
}

export class ResourceService {
    /**
     * Get Image By Query
     * Get image from local cache or download it using query parameter
     *
     * Args:
     * path: The image URL (can be non-encoded) or file hash
     * session: Database session
     *
     * Returns:
     * FileResponse: The image file
     * @param data The data for the request.
     * @param data.path
     * @returns unknown Successful Response
     * @throws ApiError
     */
    public static getImageByQuery(data: GetImageByQueryData): CancelablePromise<GetImageByQueryResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/resource/image',
            query: {
                path: data.path
            },
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Upload Image
     * Upload an image file
     *
     * Args:
     * file: The image file to upload
     * session: Database session
     *
     * Returns:
     * dict: Information about the uploaded file
     * @param data The data for the request.
     * @param data.formData
     * @returns unknown Successful Response
     * @throws ApiError
     */
    public static uploadImage(data: UploadImageData): CancelablePromise<UploadImageResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/resource/upload/image',
            formData: data.formData,
            mediaType: 'multipart/form-data',
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
}