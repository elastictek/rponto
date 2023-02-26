export const isRH = (auth, num=null) => {
    return (auth?.isRH || auth?.isAdmin) && !num;
}

export const isPrivate = (auth, num) => {
    return num;
}