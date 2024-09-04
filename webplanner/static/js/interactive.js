const student_list = $('#student_list');
const student_priority_save = $('#student_priority_save');

function build_student_list() {
    student_list.empty();
    planning_data.ordering.forEach((student_id) => {
        const student = planning_data.students[student_id];
        student_list.append($(`<li class="list-group-item list-group-item-primary" student_id="${student_id}"></li>`).text(`${student.first_name} ${student.last_name}`));
    });
    student_list.sortable({
        axis: "y"
    });
}

build_student_list();

const student_priority_modal = document.getElementById('student_priority_modal');
student_priority_modal.addEventListener('show.bs.modal', function () {
    // do something here?
    console.log("show.bs.modal");
});
student_priority_modal.addEventListener('hide.bs.modal', function () {
    // do something here?
    console.log("hide.bs.modal");
});
student_priority_save.click(() => {
    var new_student_id_list = [];
    student_list.sortable("toArray", {attribute: "student_id"}).forEach((student_id_str) => {
        new_student_id_list.push(parseInt(student_id_str));
    });
    console.log(new_student_id_list);
});