/* Add a table of contents to an HTML document.

Wikipedia automatically adds a per-page table of contents before the
first non-top-level header on a page. This makes Wikipedia articles
substantially easier to navigate, in my experience. I’ve been writing
a bunch of documents in Markdown, and I wanted to add similar tables
of contents to them.

I could have added the feature to my Markdown processing pipeline (I
already slap on a <title> in there), but I thought it would be maybe
more useful to implement the feature in JS. Then I could apply it to
any document on the web that uses proper semantic markup, not just the
ones I wrote myself.

So this script, written in JS, finds all the headers in the document
(<h1> is excluded except when there is more than one of them),
makes a table of contents, and inserts it into the
document.  You can add a table of contents to any HTML document you 
like by adding this line to the end of the document’s <body>:

    <script src="http://canonical.org/~kragen/sw/addtoc.js"></script>

(Note: if you copy and paste this code into your HTML for some reason,
you’ll probably want to remove that example line above!)

It doesn’t depend on any other JS libraries, and I’ve tried to make
sure it doesn’t conflict with them either.

(Of course, you can host it yourself, too.)

This software is licensed under the “MIT License”, which differs from
a dedication to the public domain only minimally; among other things,
it’s more enforceable in Germany, and you can’t remove the copyright
notice:

Copyright (c) 2010 Kragen Javier Sitaker

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

*/

(function() {
  // Go ahead and change this if you’re hosting the software yourself.
  var url = "http://canonical.org/~kragen/sw/addtoc.js";            

  // These have to be in caps because we’re looking up elem.tagName
  var header_rank = {H2: 2, H3: 3, H4: 4, H5: 5, H6: 6};

  if (find('h1').length > 1) header_rank.H1 = 1;

  var headers = get_list_of_headers(header_rank);
  if (!headers.length) return;

  assign_ids_if_necessary_to(headers);

  // insert ToC before the first h2 (or other header)
  insert_before(make_toc(url, header_rank, headers), headers[0]);

  // imitating current Wikipedia table of contents style
  inject_stylesheet(
    ".addtoc_toc { " +
    "  background-color: #eee; " +
    "  color: black; " +
    "  border: 1px solid #aaa; " +
    "  padding: 0.5em; " +
    "}\n" +
    // The !important is to override #foo a selectors on some pages.
    ".addtoc_toc a { color: blue !important }\n" +
    ".addtoc_title { text-align: center; font-weight: bold; margin-bottom: 0.5em }\n" +
    ".addtoc_toc * { list-style-type: none; margin: 0; padding: 0 }\n" +
    ".addtoc_toc ol ol { margin-left: 2em }\n" +
    ".addtoc_controls { display: none; font-weight: normal }\n" +
    ".addtoc_controls p { margin: 1em 0; max-width: 30em; text-align: left }\n" +
    ""
  );

  return;


  function get_list_of_headers(header_rank) {
    var headers = [];
    var stack = [document.body];

    // XXX there’s gotta be a better way
    while (stack.length) {
      var elem = stack.pop();

      if (header_rank[elem.tagName] || is_filthy_pig_header(elem)) {
        headers.push(elem);
      }

      for (var ii = elem.childNodes.length; ii > 0; ii--) {
        var subelem = elem.childNodes[ii-1];
        if (subelem.nodeType == subelem.ELEMENT_NODE) stack.push(subelem);
      }
    }

    return headers;
  }


  // Some dirty people indicate headers by writing a short paragraph
  // entirely in boldface, rather than using an actual <h3> or
  // whatever. This is an attempt to accommodate their pages; this
  // function returns true if its argument is a <b> or <strong> that
  // is the sole child of a <p>, or the only child before a <br/>, and
  // is short.
  function is_filthy_pig_header(node) {
    if (node.tagName !== 'B' && node.tagName !== 'STRONG') return false;

    if (node.innerHTML.length > 80) return false;

    if (node.parentNode.tagName !== 'P') return false;

    var siblings = node.parentNode.childNodes;
    for (var ii = 0; ii < siblings.length; ii++) {
      var sib = siblings[ii];
      if (sib === node) continue;

      if (sib.nodeType === sib.TEXT_NODE) {
        if (/^\s*$/.test(sib.textContent)) continue;
        return false;
      }

      if (sib.tagName === 'BR') return true;

      return false;
    }

    return true;
  }


  function assign_ids_if_necessary_to(headers) {
   // assign them IDs if they don’t have them
   var id_serial = 1;
   for (var ii = 0; ii < headers.length; ii++) {
     if (!headers[ii].id) {
       headers[ii].id = "addtoc_" + id_serial;
       id_serial++;
     }
   }
  }


  function make_toc(url, header_rank, headers) {
    var olStack = [{rank: 2, list: make('ol'), numbering: [0]}];
    if (header_rank.H1) olStack[0].rank = 1;

    for (var ii = 0; ii < headers.length; ii++) {
      var ahref = make('a',  headers[ii].innerHTML);
      ahref.href = "#" + headers[ii].id;
      remove_all_inner_links_from(ahref);
      remove_all_ids_from(ahref.childNodes);

      // Treat filthy pig headers as <h7>.
      var rank = header_rank[headers[ii].tagName] || 7;

      while (olStack[olStack.length-1].rank > rank) olStack.pop();
      if (olStack[olStack.length-1].rank < rank) {
        olStack.push(new_ol(rank, olStack[olStack.length-1]));
      }

      var top = olStack[olStack.length-1];

      var li = make('li');
      li.appendChild(ahref);
      add_numbering(top, li);

      top.list.appendChild(li);
    }

    var div = make('div');
    div.innerHTML = ('<table class="addtoc_toc">' +
      '<tr><td><div class="addtoc_title">Page Contents</div></tr></td>' +
      '</table>');
    var td = find('td', div)[0]
    find('div', td)[0].appendChild(make_controls(url));
    td.appendChild(olStack[0].list);

    return div;
  }


  function make_controls(url) {
    var rv = make('span', ' <a href="#">[more]</a>' +
      '<div class="addtoc_controls">hi</span>');
    var controls = find('div', rv)[0];

    var link = find('a', rv)[0]
    link.onclick = function(ev) {
      controls.style.display = 'block';
      link.style.display = 'none';
      return false;
    };

    // Note that this will be inside the "" of an <a href>, so it’s
    // not safe for it to contain "" itself.
    var bookmarklet_code = (
      "(function() {" +
      "  var s=document.createElement('script');" +
      "  s.src='"+url+"';" +
      "  document.body.appendChild(s);" +
      "})()" +
      ""
    );

    controls.innerHTML = (
      '<a href="#">[hide table of contents]</a> ' +
      '<a href="#">[hide these controls]</a> ' +
      '<p>This table-of-contents code is free software. You can use it ' +
      'on any properly-written web page you read. ' +
      'Drag the following ' +
      '<a href="https://www.squarefree.com/bookmarklets/">bookmarklet</a> ' +
      'to your browser\'s bookmark bar, and click it when you want a ToC: ' +
      '<a href="javascript:'+bookmarklet_code+'">addtoc</a>. ' +
      '<p>You can also use it in your own HTML documents. For instructions, ' +
      'please see the source code of this copy at ' +
      '<a href="'+url+'">'+url+'</a>.  Share and enjoy!' +
      '<p>Properly-marked-up web pages include Wikipedia pages ' +
      "(although there's no point), " +
      'WordPress and Blogger blogs ' +
      "(even WordPress posts sometimes, although that's up to the author), " +
      "most documents written in Markdown (e.g. Raganwald's homoiconic), " +
      "Ars Technica articles, Henry Baker's papers, " +
      "and the Lua reference manual." +
      ''
    );

    find('a', controls)[0].onclick = function() {
      inject_stylesheet(".addtoc_toc { display: none }");
      return false;
    };

    find('a', controls)[1].onclick = function() {
      controls.style.display = 'none';
      link.style.display = 'inline';
      return false;
    };

    return rv;
  }


  function remove_all_inner_links_from(domnode) {
    var links = [];
    var links_search = find('a', domnode);
    for (var ii = 0; ii < links_search.length; ii++) {
      if (links_search[ii].href) links.push(links_search[ii]);
    }
    for (var ii = 0; ii < links.length; ii++) {
      while (links[ii].childNodes.length) {
        insert_before(remove(links[ii].firstChild), links[ii]);
      }
      remove(links[ii]);
    }
  }


  function remove_all_ids_from(domnodes) {
    for (var ii = 0; ii < domnodes.length; ii++) {
      var node = domnodes[ii];
      if (node.id) node.id = undefined;
      if (node.childNodes) remove_all_ids_from(node.childNodes);
    }
  }


  function new_ol(rank, parent) {
    // If this is the top element on the stack, it might not have an
    // <li> child yet.
    if (!parent.list.childNodes.length) {
      parent.list.appendChild(make('li', '(unnamed)'));
    }

    var ol = make('ol');
    parent.list.lastChild.appendChild(ol);

    var numbering = parent.numbering.slice();
    numbering.push(0);

    return {rank: rank, list: ol, numbering: numbering};
  }


  function add_numbering(parent, domnode) {
    parent.numbering[parent.numbering.length-1]++;
    var number = parent.numbering.join(".") + ") ";
    insert_before(text(number), domnode.firstChild);
  }


  function inject_stylesheet(stylesheet) {
    var style = make('style', stylesheet);
    style.type = 'text/css';
    document.body.appendChild(style);
  }


  function make(tagname, html) {
    var elem = document.createElement(tagname);
    if (html) elem.innerHTML = html;
    return elem;
  }

  function find(tagname, where) {
    if (!where) where = document;
    return where.getElementsByTagName(tagname);
  }

  function text(text) { return document.createTextNode(text); }

  function insert_before(new_node, reference) {
    reference.parentNode.insertBefore(new_node, reference);
  }

  function remove(node) {
    node.parentNode.removeChild(node);
    return node;
  }

})();
