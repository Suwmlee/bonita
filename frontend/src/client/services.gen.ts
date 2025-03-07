// This file is auto-generated by @hey-api/openapi-ts

import type { CancelablePromise } from './core/CancelablePromise';
import { OpenAPI } from './core/OpenAPI';
import { request as __request } from './core/request';
import type { LoginAccessTokenData, LoginAccessTokenResponse, ReadUsersData, ReadUsersResponse, CreateUserData, CreateUserResponse, ReadUserMeResponse, DeleteUserMeResponse, UpdateUserMeData, UpdateUserMeResponse, UpdatePasswordMeData, UpdatePasswordMeResponse, RegisterUserData, RegisterUserResponse, ReadUserByIdData, ReadUserByIdResponse, UpdateUserData, UpdateUserResponse, DeleteUserData, DeleteUserResponse, RunTransferTaskData, RunTransferTaskResponse, GetAllTasksStatusResponse, GetAllTaskConfigsData, GetAllTaskConfigsResponse, CreateTaskConfigData, CreateTaskConfigResponse, UpdateTaskConfigData, UpdateTaskConfigResponse, DeleteTaskConfigData, DeleteTaskConfigResponse, GetAllConfigsData, GetAllConfigsResponse, CreateConfigData, CreateConfigResponse, UpdateConfigData, UpdateConfigResponse, DeleteConfigData, DeleteConfigResponse, GetRecordsData, GetRecordsResponse, UpdateRecordData, UpdateRecordResponse, DeleteRecordsData, DeleteRecordsResponse, GetTransRecordsData, GetTransRecordsResponse, GetMetadataData, GetMetadataResponse, UpdateMetadataData, UpdateMetadataResponse, DeleteMetadataData, DeleteMetadataResponse, RunImportNfoData, RunImportNfoResponse, RunEmbyScanData, RunEmbyScanResponse, GetProxySettingsResponse, UpdateProxySettingsData, UpdateProxySettingsResponse, GetImageByQueryData, GetImageByQueryResponse, UploadImageData, UploadImageResponse } from './types.gen';

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
     * @param data.requestBody
     * @returns TaskStatus Successful Response
     * @throws ApiError
     */
    public static runTransferTask(data: RunTransferTaskData): CancelablePromise<RunTransferTaskResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/tasks/run/{id}',
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
     * Get All Tasks Status
     * 获取所有任务状态
     * @returns TaskStatus Successful Response
     * @throws ApiError
     */
    public static getAllTasksStatus(): CancelablePromise<GetAllTasksStatusResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/tasks/status'
        });
    }
    
}

export class TaskConfigService {
    /**
     * Get All Task Configs
     * 获取所有任务配置
     * @param data The data for the request.
     * @param data.skip
     * @param data.limit
     * @returns TransferConfigsPublic Successful Response
     * @throws ApiError
     */
    public static getAllTaskConfigs(data: GetAllTaskConfigsData = {}): CancelablePromise<GetAllTaskConfigsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/tasks/config/all',
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
     * Create Task Config
     * 创建新任务配置
     * @param data The data for the request.
     * @param data.requestBody
     * @returns TransferConfigPublic Successful Response
     * @throws ApiError
     */
    public static createTaskConfig(data: CreateTaskConfigData): CancelablePromise<CreateTaskConfigResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/tasks/config/',
            body: data.requestBody,
            mediaType: 'application/json',
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Update Task Config
     * 更新任务配置
     * @param data The data for the request.
     * @param data.id
     * @param data.requestBody
     * @returns TransferConfigPublic Successful Response
     * @throws ApiError
     */
    public static updateTaskConfig(data: UpdateTaskConfigData): CancelablePromise<UpdateTaskConfigResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/tasks/config/{id}',
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
     * Delete Task Config
     * 删除任务配置
     * @param data The data for the request.
     * @param data.id
     * @returns Response Successful Response
     * @throws ApiError
     */
    public static deleteTaskConfig(data: DeleteTaskConfigData): CancelablePromise<DeleteTaskConfigResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/tasks/config/{id}',
            path: {
                id: data.id
            },
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
}

export class ScrapingConfigService {
    /**
     * Get All Configs
     * 获取所有配置.
     * @param data The data for the request.
     * @param data.skip
     * @param data.limit
     * @returns ScrapingConfigsPublic Successful Response
     * @throws ApiError
     */
    public static getAllConfigs(data: GetAllConfigsData = {}): CancelablePromise<GetAllConfigsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/scraping/config/all',
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
     * Create Config
     * 创建新配置
     * @param data The data for the request.
     * @param data.requestBody
     * @returns ScrapingConfigPublic Successful Response
     * @throws ApiError
     */
    public static createConfig(data: CreateConfigData): CancelablePromise<CreateConfigResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/scraping/config/',
            body: data.requestBody,
            mediaType: 'application/json',
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Update Config
     * 更新配置
     * @param data The data for the request.
     * @param data.id
     * @param data.requestBody
     * @returns ScrapingConfigPublic Successful Response
     * @throws ApiError
     */
    public static updateConfig(data: UpdateConfigData): CancelablePromise<UpdateConfigResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/scraping/config/{id}',
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
     * Delete Config
     * 删除配置
     * @param data The data for the request.
     * @param data.id
     * @returns Response Successful Response
     * @throws ApiError
     */
    public static deleteConfig(data: DeleteConfigData): CancelablePromise<DeleteConfigResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/scraping/config/{id}',
            path: {
                id: data.id
            },
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
}

export class RecordService {
    /**
     * Get Records
     * 获取记录信息 包含 ExtraInfo
     * 可以根据task_id进行精确过滤
     * search参数可同时模糊匹配srcname和srcpath
     * @param data The data for the request.
     * @param data.skip
     * @param data.limit
     * @param data.taskId
     * @param data.search
     * @returns RecordsPublic Successful Response
     * @throws ApiError
     */
    public static getRecords(data: GetRecordsData = {}): CancelablePromise<GetRecordsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/records/all',
            query: {
                skip: data.skip,
                limit: data.limit,
                task_id: data.taskId,
                search: data.search
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
     * Delete Records
     * 删除记录信息
     *
     * Args:
     * session: 数据库会话
     * record_ids: 要删除的记录ID列表
     * force: 是否强制删除，如果为True则同时删除关联的文件
     *
     * Returns:
     * 删除操作的结果
     * @param data The data for the request.
     * @param data.requestBody
     * @param data.force
     * @returns Response Successful Response
     * @throws ApiError
     */
    public static deleteRecords(data: DeleteRecordsData): CancelablePromise<DeleteRecordsResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/records/records',
            query: {
                force: data.force
            },
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

export class ToolsService {
    /**
     * Run Import Nfo
     * 导入NFO信息
     * @param data The data for the request.
     * @param data.requestBody
     * @returns TaskStatus Successful Response
     * @throws ApiError
     */
    public static runImportNfo(data: RunImportNfoData): CancelablePromise<RunImportNfoResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/tools/importnfo',
            body: data.requestBody,
            mediaType: 'application/json',
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
    /**
     * Run Emby Scan
     * 扫描emby
     * @param data The data for the request.
     * @param data.requestBody
     * @returns TaskStatus Successful Response
     * @throws ApiError
     */
    public static runEmbyScan(data: RunEmbyScanData): CancelablePromise<RunEmbyScanResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/tools/embyscan',
            body: data.requestBody,
            mediaType: 'application/json',
            errors: {
                422: 'Validation Error'
            }
        });
    }
    
}

export class SettingsService {
    /**
     * Get Proxy Settings
     * 获取代理设置.
     * @returns ProxySettings Successful Response
     * @throws ApiError
     */
    public static getProxySettings(): CancelablePromise<GetProxySettingsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/settings/proxy'
        });
    }
    
    /**
     * Update Proxy Settings
     * 更新代理设置.
     * @param data The data for the request.
     * @param data.requestBody
     * @returns Response Successful Response
     * @throws ApiError
     */
    public static updateProxySettings(data: UpdateProxySettingsData): CancelablePromise<UpdateProxySettingsResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/settings/proxy',
            body: data.requestBody,
            mediaType: 'application/json',
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