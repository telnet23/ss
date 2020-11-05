//var example = {
//  'condition': 'AND',
//  'rules': [
//    {
//      'id': 'Issue Type',
//      'field': 'Issue Type',
//      'type': 'string',
//      'input': 'select',
//      'operator': 'regex_equal',
//      'value': 'Common Stock'
//    },
//    {
//      'id': 'Dividend Yield',
//      'field': 'Dividend Yield',
//      'type': 'double',
//      'input': 'number',
//      'operator': 'greater_or_equal',
//      'value': 4.5
//    },
//    {
//      'condition': 'OR',
//      'rules': [
//        {
//          'id': 'Sector',
//          'field': 'Sector',
//          'type': 'string',
//          'input': 'select',
//          'operator': 'regex_equal',
//          'value': 'Communication Services'
//        },
//        {
//          'id': 'Sector',
//          'field': 'Sector',
//          'type': 'string',
//          'input': 'select',
//          'operator': 'regex_equal',
//          'value': 'Technology'
//        }
//      ]
//    }
//  ],
//  'valid': true
//}
$.xhrPool = []
$.xhrPool.abortAll = function() {
  $(this).each(function(i, jqXHR) {
    jqXHR.abort()
    $.xhrPool.splice(i, 1)
  })
}
$.ajaxSetup({
  beforeSend: function(jqXHR) {
    $.xhrPool.push(jqXHR)
  },
  complete: function(jqXHR) {
    $.xhrPool.splice($.xhrPool.indexOf(jqXHR), 1)
  }
})
$(document).ready(function() {
  if (! window.location.protocol.match('^http')) {
    document.body.innerHTML = ''
    return
  }
//  $.get({
//    url: './filters',
//    success: function(filters) {
//      $('#query').queryBuilder({
//        filters: filters,
//        lang_code: 'en',
//        plugins: ['sortable'],
//        select_placeholder: '',
//      })
      //var match = window.location.pathname.match(/\/q\/(.+)/)
      //if (match) {
      var path = window.location.pathname.split('/')
      var id = path[path.length - 1]
      if (id != '') {
        $.get({
          //url: './query/' + match[1],
          //url: './query/' + match[1] + '.js',
          url: './query/' + id + '.js',
          success: function(query) {
            if (typeof query == 'object') {
              $('#query').queryBuilder('setRulesFromMongo', query)
            }
            else {
              $('#symbols').focus()
              $('#symbols').text(query)
            }
          },
          error: function() {
            window.history.replaceState(null, null, './')
          }
        })
      }
//    }
//  })
  $('#query-submit').on('click', function() {
    var query = $('#query').queryBuilder('getMongo')
    submit(query)
  })
  $('#query-clear').on('click', function() {
    $('#query').queryBuilder('reset')
  })
  $('#query-example').on('click', function() {
    $('#query').queryBuilder('setRules', example)
  })
  $('#symbols-submit').on('click', function() {
    var symbols = $('#symbols').val()
    submit(symbols)
  })
  $('#symbols-clear').on('click', function() {
    $('#symbols').focus()
    $('#symbols').val('')
  })
  $('#symbols-example').on('click', function() {
    $('#symbols').focus()
    $('#symbols').val('AAPL, GOOG, MSFT\nAMZN, EBAY\nNFLX, INTC, ORCL, TSLA')
  })
})
var nsubmits = 0
function submit(data) {
  if (typeof data == 'object') {
    var mode = 'query'
  }
  else {
    var mode = 'symbols'
  }
  nsubmits += 1
  $.xhrPool.abortAll()
  $('#query-count').empty()
  $('#symbols-count').empty()
  $('#results').empty()
  $('#' + mode + '-submit').val($('#' + mode + '-submit').html())
  $('#' + mode + '-submit').addClass('disabled')
  $('#' + mode + '-submit').html('<i class="glyphicon glyphicon-refresh spin"></i> Loading...')
  $.ajax({
    type: 'POST',
    url: './query',
    data: JSON.stringify(data),
    contentType: 'application/json',
    dataType: 'json',
    success: function(response) {
      var id = response['id']
      if (id != null) {
        window.history.pushState(null, null, './' + id)
      }
      var symbols = response['symbols']
      $('#' + mode + '-count').html('Found ' + symbols.length + ' symbol' + (symbols.length == 1 ? '' : 's'))
      if (symbols.length > 0 && ! getCookie('suppressGrowl1')) {
        $.bootstrapGrowl('Use the up arrow key or down arrow key to jump to the previous symbol or next symbol, respectively.', {
          type: 'info',
          align: 'left',
          delay: 30000,
          width: 450,
        })
        setCookie('suppressGrowl1', 1, 30)
      }
      for (var i = 0; i < symbols.length; i++) {
        $('#results').append('<hr>')
        $('#results').append('<div class="result" id="' + i + '"></div>')
        //$('#' + i + '.result').append('<div class="text-center">' + symbols[i] + '</div>')
        $('#' + i + '.result').append('<div class="text-center" id="' + i + '">' + symbols[i] + '</div>')
        $('#' + i + '.result').append('<div class="chart wide" id="' + i + '">Loading chart...</div>')
//        $('#' + i + '.result').append('<div class="table wide" id="' + i + '">Loading table...</div>')
        if (i == 0) {
          $('html,body').animate({scrollTop: $('#' + i + '.result').offset().top}, 1000)
        }
        $.get({
          //url: './chart/' + symbols[i],
          url: './chart/' + symbols[i] + '.js',
          i: i,
          success: function(data) {
            function getSize() {
              return {
                height: window.innerHeight * 0.75,
                width: window.innerWidth - 16,
              }
            }
            function throttle(cb, limit) {
              var wait = false
              return () => {
                if (! wait) {
                  requestAnimationFrame(cb)
                  wait = true
                  setTimeout(() => { wait = false; }, limit)
                }
              }
            }
            var opts = {
              ...getSize(),
              cursor: { y: false, },
              axes: [
                {
                  stroke: "#ddd",
                  grid: { show: false, },
                  values: [
                    [3600 * 24 * 365, "{YYYY}", null, null, null, null, null, null, 1],
                    [3600 * 24 * 28, "{MMM}", "\n{YYYY}", null, null, null, null, null, 1],
                    [3600 * 24, "{M}/{D}", "\n{YYYY}", null, null, null, null, null, 1],
                  ],
                },
                {
                  stroke: "#ddd",
                  grid: { show: false, },
                },
              ],
              series: [
                {
                  label: 'Date',
                  value: function(self, date) {
                    var d = new Date(1000 * date)
                    return d.toLocaleDateString()
                  },
                },
                { show: false, label: 'Open', stroke: '#ffc107', width: 0.75, points: { show: false }, },
                { show: false, label: 'High', stroke: '#dc3545', width: 0.75, points: { show: false }, },
                { show: false, label: 'Low', stroke: '#007bff', width: 0.75, points: { show: false }, },
                { show: true, label: 'Close', stroke: '#28a745', width: 0.75, points: { show: false }, },
              ],
            }
            $('#' + this.i + '.chart').empty()
            var u = new uPlot(opts, data, $('#' + this.i + '.chart')[0])
            window.addEventListener("resize", throttle(() => u.setSize(getSize()), 50))
          },
          error: function() {
            $('#' + this.i + '.chart').empty()
          }
        })
//        $.get({
//          url: './table/' + symbols[i],
//          i: i,
//          success: function(table) {
//            var html = ''
//            var ncolumns = 3
//            var nrows = Math.ceil(table.length / ncolumns)
//            for (var row = 0; row < nrows; row++) {
//              html += '<tr>'
//              for (var column = 0; column < ncolumns; column++) {
//                x = column * nrows + row
//                if (x < table.length) {
//                  if (table[x][1].match(/^https?:\/\//i)) {
//                    table[x][1] = '<a href="' + table[x][1] + '" rel="noreferrer">' + table[x][1] + '</a>'
//                  }
//                  if (table[x][1].length > 25) {
//                    html += '<td>' + table[x][0] + ':</td><td class="normal"><b>' + table[x][1] + '</b></td>'
//                  }
//                  else {
//                    html += '<td>' + table[x][0] + ':</td><td><b>' + table[x][1] + '</b></td>'
//                  }
//                }
//                else {
//                  html += '<td></td><td></td>'
//                }
//              }
//              html += '</tr>'
//            }
//            $('#' + this.i + '.table').html(html)
//          },
//          error: function() {
//            $('#' + this.i + '.table').empty()
//          }
//        })
      }
    },
    error: function() {
      $('#' + mode + '-count').html('<span style="color: red;"><i class="glyphicon glyphicon-warning-sign"></i> Error</span>')
    },
    complete: function() {
      $('#' + mode + '-submit').removeClass('disabled')
      $('#' + mode + '-submit').html($('#' + mode + '-submit').val())
    }
  })
}
$(document).keydown(function(e) {
  var up = (e.which == 38)
  var down = (e.which == 40)
  if (up || down) {
    e.preventDefault()
    $('div.result').each(function(index) {
      var resultTop = $(this).offset().top
      var resultBottom = resultTop + $(this).outerHeight()
      var viewportTop = $(window).scrollTop()
      var viewportBottom = viewportTop + $(window).height()
      if (resultBottom > viewportTop && resultTop < viewportBottom) {
        if (up) {
          var next = Number($(this).attr('id')) - 1
        }
        else {
          var next = Number($(this).attr('id')) + 1
        }
        element = $('#' + next + '.result')
        if (element.length) {
          $('html,body').animate({scrollTop: element.offset().top}, 250)
        }
        else {
          if (up) {
            $('html,body').animate({scrollTop: 0}, 250)
          }
          else {
            $('html,body').animate({scrollTop: $(document).height()}, 250)
          }
        }
        return false // break
      }
    })
  }
})
function setCookie(key, value, days) {
  var date = new Date()
  date.setTime(date.getTime() + (days*24*60*60*1000))
  document.cookie = key + '=' + value + ';' + 'expires' + '=' + date.toUTCString() + ';' + 'path=/;'
}
function getCookie(key) {
  var cookies = document.cookie.split(';')
  for (var i = 0; i < cookies.length; i++) {
    var cookie = cookies[i]
    while (cookie.charAt(0) == ' ') {
      cookie = cookie.substring(1)
    }
    if (cookie.indexOf(key + '=') == 0) {
      return cookie.substring((key + '=').length, cookie.length)
    }
  }
  return ''
}
