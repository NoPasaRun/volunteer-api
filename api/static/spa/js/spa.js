async function sendRequest(url, method, success, data = null, error = async (data) => {console.log(data)}, headers = null) {
    await $.ajax({
        url: url,
        data: data,
        method: method,
        headers: headers,
        success: async (data) => {
            await success(data)
        },
        error: async (data) => {
            await error(data)
        }
    })
}

const getBase64 = file => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
});

function getTaskData(is_open, selector) {
    if (selector === "#other-tasks") {
        return {
            class_: is_open ? "" : "task__button_closed",
            text: is_open ? "Принять" : "Завершена",
            disabled: is_open ? "" : "disabled"
        }
    } else if (selector === "#my-tasks") {
        return {
            class_: is_open ? "task__button_deny" : "task__button_closed",
            text: is_open ? "Отказаться" : "Завершена",
            disabled: is_open ? "" : "disabled"
        }
    }
}

function showTasks(selector) {
    return async (data) => {
        $(selector).html("")
        data.forEach(el => {
            let td = getTaskData(el.is_open, selector)
            let str_comment_form = `
                <form class='form__comment form__comment-create'>
                    <input name='id' type='hidden' value='${el.id}'>
                    <div class="form__block">
                        <textarea name="text" required>Введите текст комментария</textarea>
                    </div>
                    <div class="form__block form__block_flex">
                        <input type="file" name="photo">
                        <button class="submit__button">
                            ОТПРАВИТЬ
                        </button>
                    </div>
                </form>
            `
            let str_task = `
                <li class='open__task'>
                    <form class='form__task form__task-accept'>
                        <input name='id' type='hidden' value='${el.id}'>
                        <span class='task__field'>${el.title}</span>
                        <span class='task__field'>${el.description}</span>
                        <button class='task__button ${td.class_}' ${td.disabled}>${td.text}</button>
                    </form>
                    <form class="form__comment-get">
                        <input name='id' type='hidden' value='${el.id}'>
                        <button class='task__button comment__button'>Загрузить комментарии</button>
                        <span class='hide__comments'>Скрыть комментарии</span>
                    </form>
                    ${el.is_open ? str_comment_form : ""}
                    <ul class="comment__list">
                    
                    </ul>
                </li>
            `
            $(selector).append(str_task)
        });
    }
}


function showMyData(data) {
    $("#my-info").html(`
        <div class='info__block'>
            <span class='info__label'>Группа</span>
            <span class='info__data'>${data.unit.title + " " + data.unit.description}</span>
        </div>
        <div class='info__block'>
            <span class='info__label'>Имя</span>
            <span class='info__data'>${data.first_name + " " + data.last_name}</span>
        </div>
        <div class='info__block'>
            <span class='info__label'>Почта</span>
            <span class='info__data'>${data.email}</span>
        </div>
        <div class='info__block'>
            <span class='info__label'>Аватар</span>
            <img class='info__image' src=${data.avatar}>
        </div>
        <div class='info__block'>
            <span class='info__label'>Баллы</span>
            <span class='info__data'>${data.score}</span>
        </div>
        `
    )
}

function reload(data = null) {
    location.reload();
}


async function openLogin(data = null) {
    $(".lk").css("display", "none")
    $(".register").css("display", "none")
    $(".login").css("display", "block")
}

function setComments(list) {
    return async (data) => {
        data.forEach(el => {
            let str_comment = `
                <li class='comment__item'>
                    <div class='info__block'>
                        <span class='info__data'>${el.volunteer.first_name + " " + el.volunteer.last_name}</span>
                        <img class='info__image' src=${el.volunteer.avatar} style="width: 50px">
                    </div>
                    <div class='info__block'>
                        <span class='info__data'>${el.text}</span>
                        <img class='info__image' src=${el.photo} style="width: 150px">
                    </div>
                </li>
            `
            $(list).append(str_comment)
        });
    }
}

async function openLk(data = null) {
    $(".login").css("display", "none")
    $(".lk").css("display", "block")
    let headers = {"Authorization": "Bearer " + data.access};

    await sendRequest("/api/task/", "GET", showTasks("#other-tasks"), null, openLogin, headers)
    $(".form__task-accept").on("submit", (event) => {
        event.preventDefault();
        let id = new FormData(event.target).get("id");
        sendRequest(`/api/my/task/${id}/`, "POST", reload, null, openLogin, headers)
    })

    await sendRequest("/api/my/task/", "GET", showTasks("#my-tasks"), null, openLogin, headers)
    $(".form__task-deny").on("submit", (event) => {
        event.preventDefault();
        let id = new FormData(event.target).get("id");
        sendRequest(`/api/my/task/${id}/`, "DELETE", reload, null, openLogin, headers)
    })
    $(".form__comment-get").on("submit", (event) => {
        event.preventDefault();
        let id = new FormData(event.target).get("id");
        sendRequest(`/api/comment/task/${id}/`, "GET",
            setComments(event.target.parentElement.querySelector(".comment__list")),
            null, openLogin, headers)
    })
    $(".form__comment-create").on("submit", async (event) => {
        event.preventDefault();
        let formData = new FormData(event.target)
        let id = formData.get("id");
        let photo = formData.get("photo").size === 0 ? null : await getBase64(formData.get("photo"));
        let data = {text: formData.get("text"), photo: photo}
        sendRequest(`/api/comment/task/${id}/`, "POST",
            (d) => {alert("Комментарий успешно добавлен!")}, data, openLogin, headers)
    })
    $(".hide__comments").on("click", (event) => {
        $(event.target.parentElement.parentElement.querySelector(".comment__list")).html("")
    })

    await sendRequest("/api/my/", "GET", showMyData, null, openLogin, headers)
}

async function main() {
    if (BLOCK === "login") {
        await openLogin()
    } else if (BLOCK === "lk") {
        await openLk({access: ACCESS})
    } else {
        $(".register").css("display", "block")
    }
}

window.onload = async () => {
    await main()

    $(".register__form").on("submit", async (event) => {
        event.preventDefault();
        let formData = new FormData(event.target);
        let json = Object.fromEntries(formData);
        json.avatar = json.avatar.size === 0 ? null : await getBase64(json.avatar);
        sendRequest("/api/my/", "POST", openLogin, json)
    })

    $(".login__form").on("submit", (event) => {
        event.preventDefault();
        let formData = new FormData(event.target);
        let json = Object.fromEntries(formData);
        sendRequest("/api/token/", "POST", openLk, json)
    })
}