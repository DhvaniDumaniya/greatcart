from itertools import product
from django.contrib import messages,auth
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from accounts.models import Account
from carts.models import Cart, CartItem

from carts.views import _cart_id
from carts.models import Cart,CartItem
import requests

from .forms import RegistrationForm
from django.views.decorators.csrf import csrf_exempt

#verification email
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage

# Create your views here.
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            username = email.split("@")[0]
            user = Account.objects.create_user(first_name=first_name,last_name=last_name,email=email,password=password,username=username)
            user.phone_number = phone_number
            user.save()
            
            
            #user activation
            current_site = get_current_site(request)
            mail_subject = 'please activate your account'
            message = render_to_string('accounts/account_verification_email.html',{
                'user':user,
                'domain':current_site,
                'uid':urlsafe_base64_encode(force_bytes(user.pk)), #encoding primary pk=user primary key
                'token':default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject,message,to=[to_email])
            send_email.send() #fire email
            #messages.success(request,'Thank you for registration with us. We have sent you a verification email to your emailaddress [ddumaniya07@gmail.com]. please verify. ')
            return redirect('/accounts/login/?command=verification&email='+email)
    else:
        form = RegistrationForm()
    context={
        'form':form,
    }
    return render(request,'accounts/register.html',context)

def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        
        
        user = auth.authenticate(email=email,password=password)
        if user is not None:
            try:
                # print('entering inside try block')
                cart = Cart.objects.get(cart_id=_cart_id(request))
                is_cart_item_exist = CartItem.objects.filter(cart=cart).exists()                
                # print(is_cart_item_exist)
                if is_cart_item_exist:
                    cart_item = CartItem.objects.filter(cart=cart)
                    # print(cart_item)
                    # getting product variations by cart id
                    product_variation = []
                    for item in cart_item:
                        variation = item.variations.all()
                        product_variation.append(list(variation))
                        
                        # get teh cart items from the user to acceshis product variation
                    cart_item = CartItem.objects.filter(user=user) #product=product
                    ex_var_list = []
                    id =  []
                    for item in cart_item:
                        existing_variation = item.variation.all()
                        ex_var_list.append(list(existing_variation))
                        id.append(item.id)
                    # for item in cart_item:
                    #     item.user = user
                    #     item.save()  
                    
                    # product_variation = [1,2,3,4,6]
                    # ex_var_list = [4,6,3,5]
                    for pr in product_variation:
                        if pr in ex_var_list:
                            index = ex_var_list.index(pr)
                            item_id = id[index]
                            item = CartItem.objects.get(id=item_id)
                            item.quantity += 1
                            item.user = user
                            item.save()
                            # print("Product Variations:", product_variation)
                            # print("Existing Variations:", ex_var_list)
                            # print("IDs:", id)

                        else:
                            cart_item = CartItem.objects.filter(cart=cart)
                            for item in cart_item:
                                item.user = user
                                item.save() 
            except:
                # print('entering inside except block')
                pass
            auth.login(request, user)
            messages.success(request,'you are now logged in.')
            #request library
            url = request.META.get('HTTP_REFERER')
            try:
                query = requests.utils.urlparse(url).query
                # print('quary -> ', query)
                # print('------')
                #next=/cart/checkout/
                params = dict(x.split('=')for x in query.split('&'))
                # print('params ->',params)
                if 'next' in params:
                    nextPage = params['next']
                    return redirect(nextPage)
            except:
                return redirect('dashboard')
        else:
            messages.error(request,'Invalid login credentials')
            return redirect('login')
    return render(request,'accounts/login.html')

@login_required(login_url = 'login')
def logout(request):
    auth.logout(request)
    messages.success(request,'you are logged out')
    return redirect('login')

def activate(request,uidb64,token):
    # return HttpResponse('ok')
    try:
        uid = urlsafe_base64_decode(uidb64).decode() #decodeuidb
        user = Account._default_manager.get(pk=uid)
    except(TypeError,ValueError,OverflowError,Account.DoesNotExist):
        user = None
        
    if user is not None and default_token_generator.check_token(user,token):
        user.is_active = True
        user.save()
        messages.success(request,'congratulation! your accoutn is activated.')
        return redirect('login')
    else:
        messages.error(request,'Invalid activation link')
        return redirect('register')
    
    
@login_required(login_url = 'login')
def dashboard(request):
    return render(request,'accounts/dashboard.html')





@csrf_exempt
def forgotPassword(request):
    if request.method == 'POST':
        email = request.POST['email']
        if Account.objects.filter(email=email).exists():
            user = Account.objects.get(email__exact=email)
            
            # reset password email
            current_site = get_current_site(request)
            mail_subject = 'reset your password'
            message = render_to_string('accounts/reset_password_email.html',{
                'user':user,
                'domain':current_site,
                'uid':urlsafe_base64_encode(force_bytes(user.pk)), #encoding primary pk=user primary key
                'token':default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject,message,to=[to_email])
            send_email.send()
            
            messages.success(request,'password reset email has been sent to your email.')
            return redirect ('login')  
        else:
            messages.error(request,'Account does not exist!')
            return redirect('forgotPassword')
    return render(request,'accounts/forgotPassword.html')



def resetpassword_validate(request,uidb64,token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode() #decodeuidb
        user = Account._default_manager.get(pk=uid)
    except(TypeError,ValueError,OverflowError,Account.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user,token):
        request.session['uid'] = uid      
        messages.success(request,'please reset your password')
        return redirect('resetPassword')
    else:
        messages.error(request,'this link has been expired!')
        return redirect('login')  
    
    
def resetPassword(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        
        if password == confirm_password:
              uid = request.session.get('uid')
              user = Account.objects.get(pk=uid)
              user.set_password(password)  
              user.save()
              messages.success(request,'password reset successful')
              return redirect('login')
        else:
            messages.error(request,'password do not match!')
            return redirect('resetPassword')
    else:
        return render(request,'accounts/resetPassword.html')