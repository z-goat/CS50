document.addEventListener('DOMContentLoaded', function() {

  document.querySelector('#inbox').addEventListener('click', () => load_mailbox('inbox'));
  document.querySelector('#sent').addEventListener('click', () => load_mailbox('sent'));
  document.querySelector('#archived').addEventListener('click', () => load_mailbox('archive'));
  document.querySelector('#compose').addEventListener('click', compose_email);

  document.querySelector('#compose-form').addEventListener('submit', send_email);

  load_mailbox('inbox');
});

function compose_email() {

  document.querySelector('#emails-view').style.display = 'none';
  document.querySelector('#email-detail-view').style.display = 'none';
  document.querySelector('#compose-view').style.display = 'block';

  document.querySelector('#compose-recipients').value = '';
  document.querySelector('#compose-subject').value = '';
  document.querySelector('#compose-body').value = '';
}

function load_mailbox(mailbox) {
  
  document.querySelector('#emails-view').style.display = 'block';
  document.querySelector('#email-detail-view').style.display = 'none';
  document.querySelector('#compose-view').style.display = 'none';

  document.querySelector('#emails-view').innerHTML = `<h3>${mailbox.charAt(0).toUpperCase() + mailbox.slice(1)}</h3>`;

  fetch(`/emails/${mailbox}`)
  .then(response => response.json())
  .then(emails => {
    emails.forEach(email => {
      const element = document.createElement('div');
      element.className = 'email-item';
      
      element.style.backgroundColor = email.read ? '#e9ecef' : 'white';
      element.style.border = '1px solid #ddd';
      element.style.padding = '10px';
      element.style.marginBottom = '5px';
      element.style.cursor = 'pointer';
      
      element.innerHTML = `
        <strong>${email.sender}</strong>
        <span style="margin-left: 20px;">${email.subject}</span>
        <span style="float: right; color: #6c757d;">${email.timestamp}</span>
      `;
      
      element.addEventListener('click', () => view_email(email.id));
      
      document.querySelector('#emails-view').append(element);
    });
  });
}

function send_email(event) {
  event.preventDefault();
  
  const recipients = document.querySelector('#compose-recipients').value;
  const subject = document.querySelector('#compose-subject').value;
  const body = document.querySelector('#compose-body').value;
  
  fetch('/emails', {
    method: 'POST',
    body: JSON.stringify({
      recipients: recipients,
      subject: subject,
      body: body
    })
  })
  .then(response => response.json())
  .then(result => {
    console.log(result);
    load_mailbox('sent');
  })
  .catch(error => {
    console.error('Error:', error);
  });
}

function view_email(email_id) {
  fetch(`/emails/${email_id}`)
  .then(response => response.json())
  .then(email => {
    document.querySelector('#emails-view').style.display = 'none';
    document.querySelector('#compose-view').style.display = 'none';
    document.querySelector('#email-detail-view').style.display = 'block';
    
    document.querySelector('#email-detail-view').innerHTML = `
      <div style="margin-bottom: 20px;">
        <strong>From:</strong> ${email.sender}<br>
        <strong>To:</strong> ${email.recipients.join(', ')}<br>
        <strong>Subject:</strong> ${email.subject}<br>
        <strong>Timestamp:</strong> ${email.timestamp}<br>
      </div>
      <div id="email-buttons" style="margin-bottom: 20px;"></div>
      <hr>
      <div style="white-space: pre-wrap;">${email.body}</div>
    `;
    
    if (!email.read) {
      fetch(`/emails/${email_id}`, {
        method: 'PUT',
        body: JSON.stringify({
          read: true
        })
      });
    }
    
    const buttonsDiv = document.querySelector('#email-buttons');
    const currentUser = document.querySelector('h2').textContent;
    
    if (email.sender !== currentUser) {
      const archiveButton = document.createElement('button');
      archiveButton.className = 'btn btn-sm btn-outline-primary';
      archiveButton.textContent = email.archived ? 'Unarchive' : 'Archive';
      archiveButton.addEventListener('click', () => {
        fetch(`/emails/${email_id}`, {
          method: 'PUT',
          body: JSON.stringify({
            archived: !email.archived
          })
        })
        .then(() => {
          load_mailbox('inbox');
        });
      });
      buttonsDiv.append(archiveButton);
    }
    
    const replyButton = document.createElement('button');
    replyButton.className = 'btn btn-sm btn-outline-primary';
    replyButton.textContent = 'Reply';
    replyButton.style.marginLeft = '10px';
    replyButton.addEventListener('click', () => reply_email(email));
    buttonsDiv.append(replyButton);
  });
}

function reply_email(email) {
  compose_email();
  
  document.querySelector('#compose-recipients').value = email.sender;
  
  let subject = email.subject;
  if (!subject.startsWith('Re: ')) {
    subject = 'Re: ' + subject;
  }
  document.querySelector('#compose-subject').value = subject;
  
  document.querySelector('#compose-body').value = `\n\nOn ${email.timestamp} ${email.sender} wrote:\n${email.body}`;
}