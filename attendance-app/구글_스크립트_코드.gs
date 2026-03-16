function doGet(e) {
  // 만약 실행 버튼을 직접 누르면 e가 없어 에러가 납니다.
  if (!e || !e.parameter) {
    return ContentService.createTextOutput("❌ 에러: 이 함수는 웹 앱 주소를 통해서만 실행할 수 있습니다. 상단의 [배포] 버튼을 이용해 주세요.").setMimeType(ContentService.MimeType.TEXT);
  }

  var action = e.parameter.action;
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  
  if (action == "getAllData") {
    var students = ss.getSheetByName("명단").getDataRange().getValues();
    var logs = ss.getSheetByName("로그").getDataRange().getValues();
    
    return ContentService.createTextOutput(JSON.stringify({
      students: arrayToObjects(students),
      logs: arrayToObjects(logs)
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

// 테스트용 함수: 시트가 잘 연결되었는지 확인하고 싶을 때 [실행] 버튼으로 이 함수를 선택해 누르세요.
function testConnection() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  Logger.log("연결된 시트 이름: " + ss.getName());
  Logger.log("발견된 시트 탭: " + ss.getSheets().map(s => s.getName()).join(", "));
}

function doPost(e) {
  var action = e.parameter.action;
  var data = JSON.parse(e.postData.contents);
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  
  if (action == "recordAttendance") {
    var sheet = ss.getSheetByName("로그");
    var today = new Date();
    var todayStr = Utilities.formatDate(today, "GMT+9", "yyyy-MM-dd");
    var timeStr = Utilities.formatDate(today, "GMT+9", "HH:mm:ss");
    
    var values = sheet.getDataRange().getValues();
    var found = false;
    
    for (var i = 1; i < values.length; i++) {
      if (values[i][0] == todayStr && values[i][1] == data.id && values[i][4] == "") {
        // 퇴실 처리
        var inTime = values[i][3];
        var outTime = today;
        // 단순 시간 계산 (분)
        var diff = Math.round((outTime.getTime() - new Date(todayStr + " " + inTime).getTime()) / 60000);
        
        sheet.getRange(i + 1, 5).setValue(timeStr);
        sheet.getRange(i + 1, 6).setValue(diff);
        found = true;
        return ContentService.createTextOutput(JSON.stringify({success: true, message: data.name + " 퇴실 완료 (" + diff + "분 연습)"})).setMimeType(ContentService.MimeType.JSON);
      }
    }
    
    if (!found) {
      // 입실 처리
      sheet.appendRow([todayStr, data.id, data.name, time_str = timeStr, "", ""]);
      return ContentService.createTextOutput(JSON.stringify({success: true, message: data.name + " 입실 완료 (" + timeStr + ")"})).setMimeType(ContentService.MimeType.JSON);
    }
  }
}

// 2차원 배열을 객체 배열로 변환 (JSON용)
function arrayToObjects(arr) {
  var headers = arr[0];
  var result = [];
  for (var i = 1; i < arr.length; i++) {
    var obj = {};
    for (var j = 0; j < headers.length; j++) {
      obj[headers[j]] = arr[i][j];
    }
    result.push(obj);
  }
  return result;
}
