// add the bar to the site


//make it log to console
if((Oidc && Oidc.Log && Oidc.Log.logger)){
    Oidc.Log.logger = console;
}

var applicationSettings = {
    authority:"https://secure-keycloak-lr-dlt1901-jenkins.apps.c2151-de.firelay.io/auth/realms/liferay-portal/",
    client_id:"test",
    redirect_uri:"https://secure-keycloak-lr-dlt1901-jenkins.apps.c2151-de.firelay.io/auth/realms/liferay-portal//protocol/openid-connect/logout",
    responseType:"id_token",
    scope:"openid email profile",
    silent_redirect_uri:"https://secure-keycloak-lr-dlt1901-jenkins.apps.c2151-de.firelay.io/auth/realms/liferay-portal/protocol/openid-connect/auth",
    //sessionChecksEnabled: true,
};

//add your client data here in order to connect
applicationSettings.client_id = "Add your own client ID here";
applicationSettings.redirect_uri = "Change this to the correct redirect URI";

var myDeltares;

window.onload=function()
{
    // create a usermanager class
    // for now invalid  applicationSettings.post_logout_redirect_uri = window.location.origin;
    myDeltares = new Oidc.UserManager(applicationSettings);
    
    //add logout redirect to button
    var logOutEl = document.getElementsByClassName("myDeltares-logout_link")[0];
    logOutEl .onclick = function(){ myDeltares.signoutRedirect() };
    
    //add login redirect to button
    var logInEl = document.getElementsByClassName("myDeltares-login_link")[0];
    logInEl.onclick = function(){ myDeltares.signinRedirect() };
    
    
    //after redirect callbacks
     if(window.location.href.indexOf("state") > -1) {
         
         myDeltares.events.addAccessTokenExpired(function(e){
             alert("Your session has expired");
         });
                  
         //on no user anymore
         myDeltares.events.addUserUnloaded(function(e){
            
            //show login button
            document.getElementsByClassName("myDeltares-login_link")[0].classList.remove("hidden");
            
            //hide logout button
            document.getElementsByClassName("myDeltares-logout_link")[0].classList.add("hidden");
            
            //hide username && avatar
            document.getElementsByClassName("myDeltares-id-container")[0].classList.add("hidden");
            document.getElementById("myDeltares-name").innerhtml="";
            var avatarEl = document.getElementById("myDeltares-avatar");
            if(avatarEl.firstElementChild)
            {
                avatarEl.firstElementChild.remove();
            }
            
            console.log("You logged out", e);
         });
         
        //on user logged in
        myDeltares.events.addUserLoaded(function(e){
            
            var myDeltaresUser = e.profile;
            var id_token = e.id_token;
            //hide login button
            document.getElementsByClassName("myDeltares-login_link")[0].classList.add("hidden");
            
            //show logout button
            var linkElement =document.getElementsByClassName("myDeltares-login_link")[0];
            linkElement.onclick = function(){ myDeltares.signinRedirect() };
            document.getElementsByClassName("myDeltares-logout_link")[0].classList.remove("hidden");
            
            //show username && avatar
            document.getElementById("myDeltares-name").appendChild(document.createTextNode(myDeltaresUser.given_name));
            var Avatar = document.createElement("img");
            
            //get request from liferay for user avatar with user.sub
            var LiferayImage = false;
            if (LiferayImage)
            {
                Avatar.src= LiferayImage;
                document.getElementById("myDeltares-avatar").appendChild(Avatar);
            }
            
            document.getElementsByClassName("myDeltares-id-container")[0].classList.remove("hidden");
            
             // Dispatch event
            var myDeltaresLoginEvent = new CustomEvent('myDeltares_loggedIn');
            myDeltaresLoginEvent.user = myDeltaresUser;
            myDeltaresLoginEvent.token = id_token;
            document.dispatchEvent(myDeltaresLoginEvent);
            
            //console.log("Welcome "+ myDeltaresUser.given_name, myDeltaresUser);
        });

        myDeltares.signinRedirectCallback(window.location);
        var applicationURL = window.location.href.substr(0, window.location.href.indexOf("state"));
        window.history.pushState(window.location.href, 'myDeltares', applicationURL);
    }
    
    // after login this listener is triggered
    document.addEventListener('myDeltares_loggedIn', function (e) {
        console.log("Welcome "+ e.user.given_name, e.user);
        //also use e.token for serverside authorisation
    }, false);

};