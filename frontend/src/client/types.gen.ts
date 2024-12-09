// This file is auto-generated by @hey-api/openapi-ts

export type Body_login_login_access_token = {
    grant_type?: string | null;
    username: string;
    password: string;
    scope?: string;
    client_id?: string | null;
    client_secret?: string | null;
};

export type HTTPValidationError = {
    detail?: Array<ValidationError>;
};

export type Response = {
    success?: boolean;
    message?: string | null;
    data?: {
    [key: string]: unknown;
} | Array<unknown> | null;
};

export type ScrapingSettingCreate = {
    name: string;
    description: string;
    save_metadata?: boolean | null;
    scraping_sites?: string | null;
    location_rule?: string | null;
    naming_rule?: string | null;
    max_title_len?: number | null;
};

/**
 * Properties to return via API, id is always required
 */
export type ScrapingSettingPublic = {
    name: string;
    description: string;
    save_metadata?: boolean | null;
    scraping_sites?: string | null;
    location_rule?: string | null;
    naming_rule?: string | null;
    max_title_len?: number | null;
    id: number;
};

export type ScrapingSettingsPublic = {
    data: Array<ScrapingSettingPublic>;
    count: number;
};

export type TaskBase = {
    id: string;
};

export type TaskStatus = {
    id: string;
    status?: string | null;
    detail?: string | null;
};

export type Token = {
    access_token: string;
    token_type?: string;
};

export type TransferTaskCreate = {
    name: string;
    description: string;
    enabled?: boolean;
    task_type?: number;
    content_type?: number;
    transfer_type: number;
    auto_watch?: boolean;
    clean_others?: boolean;
    optimize_name?: boolean;
    source_folder: string;
    output_folder?: string | null;
    failed_folder?: string | null;
    escape_folder?: string | null;
    escape_literals?: string | null;
    escape_size?: number | null;
    threads_num?: number | null;
    sc_enabled?: boolean;
    sc_id?: number | null;
};

/**
 * Properties to return via API, id is always required
 */
export type TransferTaskPublic = {
    name: string;
    description: string;
    enabled?: boolean;
    task_type?: number;
    content_type?: number;
    transfer_type?: number;
    auto_watch?: boolean;
    clean_others?: boolean;
    optimize_name?: boolean;
    source_folder: string;
    output_folder?: string | null;
    failed_folder?: string | null;
    escape_folder?: string | null;
    escape_literals?: string | null;
    escape_size?: number | null;
    threads_num?: number | null;
    sc_enabled?: boolean;
    sc_id?: number | null;
    id: number;
};

export type TransferTasksPublic = {
    data: Array<TransferTaskPublic>;
    count: number;
};

export type UpdatePassword = {
    current_password: string;
    new_password: string;
};

export type UserCreate = {
    name?: string | null;
    email: string;
    is_active?: boolean;
    is_superuser?: boolean;
    password: string;
};

export type UserPublic = {
    name?: string | null;
    email: string;
    is_active?: boolean;
    is_superuser?: boolean;
    id: number;
};

export type UserRegister = {
    email: string;
    password: string;
    name?: string | null;
};

export type UserUpdate = {
    name?: string | null;
    email?: string | null;
    is_active?: boolean;
    is_superuser?: boolean;
    password?: string | null;
};

export type UserUpdateMe = {
    name?: string | null;
    email?: string | null;
};

export type UsersPublic = {
    data: Array<UserPublic>;
    count: number;
};

export type ValidationError = {
    loc: Array<(string | number)>;
    msg: string;
    type: string;
};

export type LoginAccessTokenData = {
    formData: Body_login_login_access_token;
};

export type LoginAccessTokenResponse = Token;

export type ReadUsersData = {
    limit?: number;
    skip?: number;
};

export type ReadUsersResponse = UsersPublic;

export type CreateUserData = {
    requestBody: UserCreate;
};

export type CreateUserResponse = UserPublic;

export type ReadUserMeResponse = UserPublic;

export type DeleteUserMeResponse = Response;

export type UpdateUserMeData = {
    requestBody: UserUpdateMe;
};

export type UpdateUserMeResponse = UserPublic;

export type UpdatePasswordMeData = {
    requestBody: UpdatePassword;
};

export type UpdatePasswordMeResponse = Response;

export type RegisterUserData = {
    requestBody: UserRegister;
};

export type RegisterUserResponse = UserPublic;

export type ReadUserByIdData = {
    userId: number;
};

export type ReadUserByIdResponse = UserPublic;

export type UpdateUserData = {
    requestBody: UserUpdate;
    userId: number;
};

export type UpdateUserResponse = UserPublic;

export type DeleteUserData = {
    userId: number;
};

export type DeleteUserResponse = Response;

export type RunTransferTaskData = {
    id: number;
};

export type RunTransferTaskResponse = TaskBase;

export type GetTaskStatusData = {
    taskId: string;
};

export type GetTaskStatusResponse = TaskStatus;

export type GetAllTasksData = {
    limit?: number;
    skip?: number;
};

export type GetAllTasksResponse = TransferTasksPublic;

export type CreateTaskData = {
    requestBody: TransferTaskCreate;
};

export type CreateTaskResponse = TransferTaskPublic;

export type UpdateTaskData = {
    id: number;
    requestBody: TransferTaskPublic;
};

export type UpdateTaskResponse = TransferTaskPublic;

export type DeleteTaskData = {
    id: number;
};

export type DeleteTaskResponse = Response;

export type GetAllSettingsData = {
    limit?: number;
    skip?: number;
};

export type GetAllSettingsResponse = ScrapingSettingsPublic;

export type CreateSettingData = {
    requestBody: ScrapingSettingCreate;
};

export type CreateSettingResponse = ScrapingSettingPublic;

export type UpdateSettingData = {
    id: number;
    requestBody: ScrapingSettingPublic;
};

export type UpdateSettingResponse = ScrapingSettingPublic;

export type DeleteSettingData = {
    id: number;
};

export type DeleteSettingResponse = Response;

export type $OpenApiTs = {
    '/api/v1/login/access-token': {
        post: {
            req: LoginAccessTokenData;
            res: {
                /**
                 * Successful Response
                 */
                200: Token;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
    };
    '/api/v1/users/': {
        get: {
            req: ReadUsersData;
            res: {
                /**
                 * Successful Response
                 */
                200: UsersPublic;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
        post: {
            req: CreateUserData;
            res: {
                /**
                 * Successful Response
                 */
                200: UserPublic;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
    };
    '/api/v1/users/me': {
        get: {
            res: {
                /**
                 * Successful Response
                 */
                200: UserPublic;
            };
        };
        delete: {
            res: {
                /**
                 * Successful Response
                 */
                200: Response;
            };
        };
        patch: {
            req: UpdateUserMeData;
            res: {
                /**
                 * Successful Response
                 */
                200: UserPublic;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
    };
    '/api/v1/users/me/password': {
        patch: {
            req: UpdatePasswordMeData;
            res: {
                /**
                 * Successful Response
                 */
                200: Response;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
    };
    '/api/v1/users/signup': {
        post: {
            req: RegisterUserData;
            res: {
                /**
                 * Successful Response
                 */
                200: UserPublic;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
    };
    '/api/v1/users/{user_id}': {
        get: {
            req: ReadUserByIdData;
            res: {
                /**
                 * Successful Response
                 */
                200: UserPublic;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
        patch: {
            req: UpdateUserData;
            res: {
                /**
                 * Successful Response
                 */
                200: UserPublic;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
        delete: {
            req: DeleteUserData;
            res: {
                /**
                 * Successful Response
                 */
                200: Response;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
    };
    '/api/v1/task/run/{id}': {
        post: {
            req: RunTransferTaskData;
            res: {
                /**
                 * Successful Response
                 */
                200: TaskBase;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
    };
    '/api/v1/task/{task_id}': {
        get: {
            req: GetTaskStatusData;
            res: {
                /**
                 * Successful Response
                 */
                200: TaskStatus;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
    };
    '/api/v1/tasks/transfer/all': {
        get: {
            req: GetAllTasksData;
            res: {
                /**
                 * Successful Response
                 */
                200: TransferTasksPublic;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
    };
    '/api/v1/tasks/transfer/': {
        post: {
            req: CreateTaskData;
            res: {
                /**
                 * Successful Response
                 */
                200: TransferTaskPublic;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
    };
    '/api/v1/tasks/transfer/{id}': {
        put: {
            req: UpdateTaskData;
            res: {
                /**
                 * Successful Response
                 */
                200: TransferTaskPublic;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
        delete: {
            req: DeleteTaskData;
            res: {
                /**
                 * Successful Response
                 */
                200: Response;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
    };
    '/api/v1/scraping/settings/all': {
        get: {
            req: GetAllSettingsData;
            res: {
                /**
                 * Successful Response
                 */
                200: ScrapingSettingsPublic;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
    };
    '/api/v1/scraping/settings/': {
        post: {
            req: CreateSettingData;
            res: {
                /**
                 * Successful Response
                 */
                200: ScrapingSettingPublic;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
    };
    '/api/v1/scraping/settings/{id}': {
        put: {
            req: UpdateSettingData;
            res: {
                /**
                 * Successful Response
                 */
                200: ScrapingSettingPublic;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
        delete: {
            req: DeleteSettingData;
            res: {
                /**
                 * Successful Response
                 */
                200: Response;
                /**
                 * Validation Error
                 */
                422: HTTPValidationError;
            };
        };
    };
};